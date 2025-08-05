#-------------------------------------------------------------------------------
#
# Load and update VirES product collections.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020 EOX IT Services GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------
# pylint: disable=missing-docstring, too-few-public-methods

import sys
import json
from traceback import print_exc
from django.db import transaction
from vires.data import PRODUCT_COLLECTIONS
from vires.models import (
    ProductCollection, ProductType, Spacecraft, CachedMagneticModel,
)
from vires.magnetic_models import ModelLoadError
from .._common import Subcommand
from ...api.cached_magnetic_model import parse_source_model


class ImportProductCollectionSubcommand(Subcommand):
    name = "import"
    help = "Import product collection definitions from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input JSON file-name. "
            )
        )
        parser.add_argument(
            "-d", "--default", dest="load_defaults", action="store_true",
            default=False, help="Import default product collections."
        )

    def handle(self, **kwargs):
        filename = kwargs['filename']
        if kwargs['load_defaults']:
            self.info("Loading default product collections ...")
            filename = PRODUCT_COLLECTIONS

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.save_product_collections(json.load(file_), **kwargs)

    def save_product_collections(self, data, **kwargs):
        total_count = 0
        failed_count = 0
        created_count = 0
        updated_count = 0

        for item in data:
            identifier = item.get("name")
            events = []
            try:
                is_updated = save_product_collection(item, events)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to create or update product collection %s! %s",
                    identifier, error
                )
            else:
                updated_count += is_updated
                created_count += not is_updated
                for event in events:
                    self.logger.info("%s", event)

                #self.logger.info(
                #    "product collection %s updated" if is_updated else
                #    "product collection %s created", identifier
                #)
            finally:
                total_count += 1

        if created_count or total_count == 0:
            self.info(
                "%d of %d product collection%s created.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d product collection%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d product collection%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )

        sys.exit(failed_count)


@transaction.atomic
def save_product_collection(data, events):
    identifier = data.pop("name")
    for key in ["updated", "removed", "maxProductDuration"]:
        data.pop(key, None)
    is_updated, product_collection = get_product_collection(identifier)
    product_collection.type = get_product_type(data.pop("productType"))
    product_collection.spacecraft = get_spacecraft(
        data.pop("mission", None),
        data.pop("spacecraft", None),
        events=events,
    )
    product_collection.grade = data.pop("grade", None) or None
    product_collection.metadata = data
    product_collection.save()
    events.append(
        f"product collection {identifier} "
        f"{'updated' if is_updated else 'created'}"
    )
    update_cached_models(product_collection, events=events)
    return is_updated


def get_product_collection(identifier):
    try:
        return True, ProductCollection.objects.get(identifier=identifier)
    except ProductCollection.DoesNotExist:
        return False, ProductCollection(identifier=identifier)


def get_product_type(identifier):
    return ProductType.objects.get(identifier=identifier)


def get_spacecraft(mission, spacecraft, events):

    def _create_spacecraft(mission, spacecraft):
        spacecraft = Spacecraft(mission=mission, spacecraft=spacecraft)
        spacecraft.save()
        return spacecraft

    if not mission:
        return None

    try:
        spacecraft = Spacecraft.objects.get(mission=mission, spacecraft=spacecraft)
    except Spacecraft.DoesNotExist:
        spacecraft = _create_spacecraft(mission, spacecraft)
        events.append(f"spacecraft {spacecraft.as_string} created")

    return spacecraft


def update_cached_models(collection, events):
    """ Update configuration of the cached magnetic models. """

    def _parse_source_models(models):
        for source_model_expression in models:
            try:
                yield parse_source_model(source_model_expression)
            except ModelLoadError as error:
                events.append(
                    f"Skipping cached model {source_model_expression}. "
                    "The model has likely not been initialized yet. "
                    "Fix the model and reload the product collection again."
                )

    if "modelOptions" not in collection.metadata:
        return

    metadata = collection.metadata

    models = metadata["modelOptions"].pop("cachedModels", None) or []

    models = list(_parse_source_models(models))

    remove_cached_models(collection, models, events)

    for model in models:
        update_cached_model(collection, model, events)

    collection.metadata = metadata
    collection.save()


def update_cached_model(collection, model, events):
    try:
        db_model = CachedMagneticModel.objects.get(
            collection=collection, name=model.name
        )
        db_model.expression = model.expression
        db_model.metadata = {}
        event = "updated"
    except CachedMagneticModel.DoesNotExist:
        db_model = CachedMagneticModel(
            collection=collection,
            name=model.name,
            expression=model.expression,
            metadata={},
        )
        event = "created"
    db_model.save()
    events.append(
        f"cached magnetic model {collection.identifier}/{model.name} {event}"
    )


def remove_cached_models(collection, models, events):
    db_models = (
        CachedMagneticModel.objects
        .filter(collection=collection)
        .exclude(name__in=[model.name for model in models])
    )

    for db_model in db_models:
        events.append(
            f"cached magnetic model {collection.identifier}/{db_model.name} "
            "removed"
        )

    db_models.delete()
