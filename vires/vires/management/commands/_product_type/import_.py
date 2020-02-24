#-------------------------------------------------------------------------------
#
# Load and update VirES product types.
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
from logging import getLogger
from traceback import print_exc
from django.db import transaction
from vires.data import PRODUCT_TYPES
from vires.models import ProductType
from .._common import Subcommand


class ImportProductTypeSubcommand(Subcommand):
    name = "import"
    help = "Import product type definitions from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default=PRODUCT_TYPES, help=(
                "Optional input JSON file-name. "
                "Defaults to the definition of the standard product types. "
            )
        )

    def handle(self, **kwargs):
        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.load_product_types(json.load(file_), **kwargs)

    def load_product_types(self, data, **kwargs):
        failed_count = 0
        created_count = 0
        updated_count = 0

        for item in data:
            identifier = item.get("name")
            try:
                is_updated = save_product_type(item)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to create or update product type %s! %s",
                    identifier, error
                )
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info(
                    "Existing product type %s updated." if is_updated else
                    "New product type %s created.", identifier, log=True
                )

        if created_count:
            self.info(
                "%d of %d product type%s created.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d product type%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d product type%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )


@transaction.atomic
def save_product_type(data):
    identifier = data.pop("name")
    for key in ["updated", "removed"]:
        data.pop(key, None)
    is_updated, product_type = get_product_type(identifier)
    product_type.definition = data
    product_type.save()
    return is_updated


def get_product_type(identifier):
    try:
        return True, ProductType.objects.get(identifier=identifier)
    except ProductType.DoesNotExist:
        return False, ProductType(identifier=identifier)
