#-------------------------------------------------------------------------------
#
# Deregister products
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
from vires.models import Product
from .._common import Subcommand


class DeregisterProductSubcommand(Subcommand):
    name = "deregister"
    help = "Deregister products."

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all products."
        )
        parser.add_argument(
            "-t", "--product-type", dest="product_type", action='append', help=(
                "Optional filter on the collection product type. "
                "Multiple product types are allowed."
            )
        )
        parser.add_argument(
            "-c", "--collection", "--product-collection",
            dest="product_collection", action="append",
            help=(
                "Optional filter on the product collection. "
                "Multiple product collection are allowed."
            )
        )

    def handle(self, **kwargs):
        query = Product.objects.prefetch_related('collection').order_by("identifier")

        product_types = set(kwargs['product_type'] or [])
        if product_types:
            query = query.filter(collection__type__identifier__in=product_types)

        product_collections = set(kwargs['product_collection'] or [])
        if product_collections:
            query = query.filter(collection__identifier__in=product_collections)

        identifiers = set(kwargs['identifier'])
        if identifiers or not kwargs['select_all']:
            query = query.filter(identifier__in=identifiers)

        if not identifiers and not kwargs['select_all']:
            self.warning(
                "No identifier selected and no product will be removed. "
                "Use the --all option to remove all matched items."
            )

        self.deregister_products(query.all(), **kwargs)

    def deregister_products(self, products, **kwargs):
        total_count = 0
        failed_count = 0
        removed_count = 0

        for product in products:
            identifier = product.identifier
            collection_id = product.collection.identifier

            try:
                with transaction.atomic():
                    product.delete()
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to deregister product %s from collection %s! %s",
                    identifier, collection_id, error
                )
            else:
                removed_count += 1
                self.info(
                    "Product %s deregistered from %s.",
                    identifier, collection_id, log=True
                )
            finally:
                total_count += 1

        if removed_count:
            self.info(
                "%d of %d matched product%s deregistered.",
                removed_count, total_count, "s" if removed_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d matched product%s failed to be deregistered.",
                failed_count, total_count, "s" if failed_count > 1 else ""
            )
