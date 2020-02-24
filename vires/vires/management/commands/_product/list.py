#-------------------------------------------------------------------------------
#
# List products
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

from vires.models import Product
from .._common import Subcommand


class ListProductSubcommand(Subcommand):
    name = "list"
    help = "List product identifiers."

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
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
        query = Product.objects.order_by("identifier")

        product_types = set(kwargs['product_type'] or [])
        if product_types:
            query = query.filter(collection__type__identifier__in=product_types)

        product_collections = set(kwargs['product_collection'] or [])
        if product_collections:
            query = query.filter(collection__identifier__in=product_collections)

        identifiers = set(kwargs['identifier'])
        if identifiers:
            query = query.filter(identifier__in=identifiers)

        for product in query.all():
            print(product.identifier)
