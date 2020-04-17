#-------------------------------------------------------------------------------
#
# Import VirES product records
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
from django.utils.dateparse import parse_datetime
from vires.time_util import naive_to_utc
from vires.models import Product
from vires.management.api.product import (
    get_product,
    deregister_product,
    import_product,
)
from .common import ProductSelectionSubcommand


class ImportProductSubcommand(ProductSelectionSubcommand):
    name = "import"
    help = "Import product records from a JSON file."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input JSON file-name. "
                "By default, the product definitions are read from standard "
                "input."
            )
        )
        parser.add_argument(
            "--sync", "--remove-missing", dest="remove_missing",
            action="store_true", default=False, help=(
                "Synchronize the product records with the input, i.e., "
                "de-register products not present in the input JSON."
            )
        )
        parser.add_argument(
            "--update", dest="update_existing",
            action="store_true", default=False, help=(
                "Update existing records. By default the existing records "
                "are not updated."
            )
        )

    def handle(self, **kwargs):
        products = self.select_products(
            Product.objects.prefetch_related('collection', 'collection__type'),
            **kwargs
        )

        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.import_products(json.load(file_), products, **kwargs)

    def import_products(self, data, products, **kwargs):
        import_counter = ImportCounter()
        removal_counter = RemovalCounter()

        if kwargs["remove_missing"]:
            self._remove_products(data, products, removal_counter, **kwargs)

        self._import_products(data, import_counter, **kwargs)

        import_counter.print_summary(self.info)
        removal_counter.print_summary(self.info)

        sys.exit(import_counter.failed or removal_counter.failed)

    def _import_products(self, data, counter, **kwargs):
        """ Update or insert products' records. """
        record_filter = RecordFilter(**kwargs)
        update_existing = kwargs['update_existing']

        for item in data:
            collection_id = item.get("collection")
            identifier = item.get("identifier")
            try:
                record = parse_product_record(item)
                if record_filter(record):
                    result = import_product(record, update_existing, logger=self.logger)
                else:
                    result = None
            except Exception as error:
                counter.failed += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to import product %s/%s! %s",
                    collection_id, identifier, error
                )
            else:
                if result.inserted:
                    counter.created += 1
                elif result.updated:
                    counter.updated += 1
                else:
                    counter.skipped += 1
            finally:
                counter.total += 1

    def _remove_products(self, data, products, counter, **kwargs):
        """ Remove products not present in the imported product records. """

        removed_products = set(
            (product.collection.identifier, product.identifier)
            for product in products
        )
        removed_products.difference_update(
            (item.get('collection'), item.get("identifier"))
            for item in data
        )

        for collection_id, identifier in removed_products:
            try:
                deregister_product(
                    get_product(collection_id, identifier), logger=self.logger
                )
            except Exception as error:
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to de-register product %s from collection %s! %s",
                    identifier, collection_id, error
                )
                counter.failed += 1
            else:
                counter.removed += 1
            finally:
                counter.total += 1


def parse_product_record(data):
    try:
        return {
            "identifier": data["identifier"],
            "collection": data["collection"],
            "product_type": data.get("productType"),
            "begin_time": naive_to_utc(parse_datetime(data["beginTime"])),
            "end_time": naive_to_utc(parse_datetime(data["endTime"])),
            "created": (
                naive_to_utc(parse_datetime(data["created"]))
                if "created" in data else None
            ),
            "updated": (
                naive_to_utc(parse_datetime(data["updated"]))
                if "updated" in data else None
            ),
            "datasets": data['datasets'],
            "metadata": data.get('meatadata') or {},
        }
    except KeyError as key:
        missing_key = str(key)
    raise ValueError("Missing mandatory key %s!" % missing_key)


class RecordFilter():

    def __call__(self, record):
        for predicate in self._predicates:
            if not predicate(record):
                return False
        return True

    def __init__(self, **kwargs):
        self._predicates = list(self._create_predictas(**kwargs))

    @classmethod
    def _create_predictas(cls, **kwargs):
        # Note that the --invalid-only option applies only to the removed products.

        if kwargs['after']:
            yield cls._gte('begin_time', kwargs['after'])

        if kwargs['before']:
            yield cls._lt('end_time', kwargs['before'])

        if kwargs['created_after']:
            yield cls._gte('created', kwargs['created_after'])

        if kwargs['created_before']:
            yield cls._lt('created', kwargs['created_before'])

        if kwargs['updated_after']:
            yield cls._gte('updated', kwargs['updated_after'])

        if kwargs['updated_before']:
            yield cls._lt('updated', kwargs['updated_before'])

        product_types = set(kwargs['product_type'] or [])
        if product_types:
            yield cls._in('product_type', product_types)

        product_collections = set(kwargs['product_collection'] or [])
        if product_collections:
            yield cls._in('collection', product_collections)

        identifiers = set(kwargs['identifier'])
        if identifiers:
            yield cls._in('identifier', product_collections)

    @staticmethod
    def _in(key, parameter):
        def _in_predicate(record):
            value = record.get(key)
            return value is not None and value in parameter
        return _in_predicate

    @staticmethod
    def _gte(key, parameter):
        def _gte_predicate(record):
            value = record.get(key)
            return value is not None and value >= parameter
        return _gte_predicate

    @staticmethod
    def _lt(key, parameter):
        def _lt_predicate(record):
            value = record.get(key)
            return value is not None and value >= parameter
        return _lt_predicate


class ImportCounter():

    def __init__(self):
        self.failed = 0
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.total = 0

    def print_summary(self, print_function):
        if self.created or self.total == 0:
            print_function(
                "%d of %d product%s registered.",
                self.created, self.total,
                "s" if self.created > 1 else ""
            )

        if self.updated:
            print_function(
                "%d of %d product%s updated.",
                self.updated, self.total,
                "s" if self.updated > 1 else ""
            )

        if self.skipped:
            print_function(
                "%d of %d product%s skipped.",
                self.skipped, self.total,
                "s" if self.skipped > 1 else ""
            )

        if self.failed:
            print_function(
                "%d of %d product%s failed to be imported",
                self.failed, self.total,
                "s" if self.failed > 1 else ""
            )


class RemovalCounter():

    def __init__(self):
        self.failed = 0
        self.removed = 0
        self.total = 0

    def print_summary(self, print_function):
        if self.removed:
            print_function(
                "%d of %d product%s de-registered.",
                self.removed, self.total,
                "s" if self.removed > 1 else ""
            )

        if self.failed:
            print_function(
                "%d of %d product%s failed to be removed",
                self.failed, self.total,
                "s" if self.failed > 1 else ""
            )
