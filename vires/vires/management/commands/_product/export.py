#-------------------------------------------------------------------------------
#
# Export product records in JSON format.
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
from vires.models import Product
from vires.management.api.product import export_product
from .._common import JSON_OPTS, datetime_to_string
from .common import ProductSelectionSubcommand


class ExportProductSubcommand(ProductSelectionSubcommand):
    name = "export"
    help = "Export product records in JSON format."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file-name", dest="file", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        products = self.select_products(
            Product.objects.prefetch_related('collection', 'collection__type'),
            **kwargs
        )

        data = [
            serialize_product_record(export_product(product))
            for product in products
        ]

        filename = kwargs["file"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def serialize_product_record(record):
    return {
        "identifier": record['identifier'],
        "beginTime": datetime_to_string(record['begin_time']),
        "endTime": datetime_to_string(record['end_time']),
        "created": datetime_to_string(record['created']),
        "updated": datetime_to_string(record['updated']),
        "collection": record['collection'],
        "productType": record['product_type'],
        "metadata": record['metadata'],
        "datasets": record['datasets'],
    }
