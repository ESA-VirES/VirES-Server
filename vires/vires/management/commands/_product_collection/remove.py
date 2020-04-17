#-------------------------------------------------------------------------------
#
# Remove product collections
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
from traceback import print_exc
from django.db import transaction
from vires.models import ProductCollection
from .._common import Subcommand


class RemoveProductCollectionSubcommand(Subcommand):
    name = "remove"
    help = "Remove product collections."

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all product collections."
        )
        parser.add_argument(
            "-t", "--product-type", dest="product_type", action='append', help=(
                "Optional filter on the collection product types. "
                "Multiple product types are allowed."
            )
        )

    def handle(self, **kwargs):
        query = ProductCollection.objects.order_by('identifier')

        product_types = set(kwargs['product_type'] or [])
        if product_types:
            query = query.filter(type__identifier__in=product_types)

        identifiers = set(kwargs['identifier'])
        if identifiers or not kwargs['select_all']:
            query = query.filter(identifier__in=identifiers)

        if not identifiers and not kwargs['select_all']:
            self.warning(
                "No identifier selected and no collection will be removed. "
                "Use the --all option to remove all matched items."
            )

        self.remove_product_collections(query.all(), **kwargs)

    def remove_product_collections(self, product_collections, **kwargs):
        total_count = 0
        failed_count = 0
        removed_count = 0

        for product_collection in product_collections:
            identifier = product_collection.identifier

            try:
                with transaction.atomic():
                    product_collection.delete()
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to remove product collection %s! %s",
                    identifier, error
                )
            else:
                removed_count += 1
                self.logger.info("product collection %s removed", identifier)
            finally:
                total_count += 1

        if removed_count or total_count == 0:
            self.info(
                "%d of %d matched product collection%s removed.",
                removed_count, total_count, "s" if removed_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d matched product collection%s failed to be removed",
                failed_count, total_count, "s" if failed_count > 1 else ""
            )

        sys.exit(failed_count)
