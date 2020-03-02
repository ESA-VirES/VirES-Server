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
from django.db import transaction
from django.utils.dateparse import parse_datetime
from vires.time_util import naive_to_utc
from vires.models import ProductCollection, Product
from .._common import Subcommand
from .register import update_max_product_duration


class ImportProductSubcommand(Subcommand):
    name = "import"
    help = "Import product records from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input JSON file-name. "
                "By default, the product definitions are read from standard "
                "input."
            )
        )

    def handle(self, **kwargs):
        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.save_products(json.load(file_), **kwargs)

    def save_products(self, data, **kwargs):
        failed_count = 0
        created_count = 0
        updated_count = 0

        for item in data:
            collection_id = item.get("collection")
            identifier = item.get("identifier")
            try:
                is_updated = save_product(item)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to create or update product %s/%s! %s",
                    collection_id, identifier, error
                )
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info(
                    "%s/%s updated" if is_updated else "%s/%s created",
                    collection_id, identifier, log=True
                )

        if created_count:
            self.info(
                "%d of %d product%s created.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d product%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d product%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )


@transaction.atomic
def save_product(data):
    identifier = data["identifier"]
    collection = get_product_collection(data["collection"])
    product_type = data.get("productType")
    if product_type is not None and product_type != collection.type.identifier:
        raise ValueError("Collection product type mismatch!")
    is_updated, product = get_product(collection, identifier)
    product.begin_time = naive_to_utc(parse_datetime(data["beginTime"]))
    product.end_time = naive_to_utc(parse_datetime(data["endTime"]))
    product.datasets = data['datasets']
    product.metadata = data.get('meatadata') or {}
    product.save()
    update_max_product_duration(collection, product.end_time - product.begin_time)
    return is_updated


def get_product(collection, identifier):
    try:
        return True, collection.products.get(identifier=identifier)
    except Product.DoesNotExist:
        return False, Product(identifier=identifier, collection=collection)


def get_product_collection(identifier):
    return ProductCollection.objects.select_related('type').get(identifier=identifier)
