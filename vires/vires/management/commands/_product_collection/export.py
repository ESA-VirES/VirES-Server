#-------------------------------------------------------------------------------
#
# Export product collections in JSON format.
#
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
# pylint: disable=missing-docstring

import sys
import json
from vires.models import ProductCollection
from vires.time_util import format_timedelta, format_datetime
from .._common import JSON_OPTS
from .common import ProductCollectionSelectionSubcommand


class ExportProductCollectionSubcommand(ProductCollectionSelectionSubcommand):
    name = "export"
    help = "Export product collection definitions as a JSON file."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        query = (
            ProductCollection.objects
            .prefetch_related("type", "spacecraft", "cached_magnetic_models")
            .order_by("identifier")
        )

        query = self.select_collections(query, **kwargs)

        data = [serialize_collection(collection) for collection in query.all()]

        filename = kwargs["filename"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def serialize_collection(object_):
    return {
        "name": object_.identifier,
        "productType": object_.type.identifier,
        "created": format_datetime(object_.created),
        "updated": format_datetime(object_.updated),
        "maxProductDuration": format_timedelta(object_.max_product_duration),
        **export_metadata(object_, object_.metadata),
    }


def export_metadata(collection, metadata):
    metadata = {
        **collection.spacecraft_dict,
        **({"grade": collection.grade} if collection.grade else {}),
        **collection.metadata,
    }
    metadata = export_cached_models(collection, metadata)
    return metadata


def export_cached_models(collection, metadata):
    if collection.cached_magnetic_models.count() > 0:
        metadata["modelOptions"] = {
            **(metadata.get("modelOptions") or {}),
            "cachedModels": [
                model.expression
                for model in collection.cached_magnetic_models.all()
            ],
        }
    return metadata
