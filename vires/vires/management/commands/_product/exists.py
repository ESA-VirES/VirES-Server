#-------------------------------------------------------------------------------
#
# Check existence of one more products.
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
from vires.models import Product
from .common import ProductSelectionSubcommand


class ExistsProductSubcommand(ProductSelectionSubcommand):
    name = "exists"
    help = "Check product existence."

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs=1)
        parser.add_argument(
            "--not", dest="negate", action="store_true",
            default=False, help="Negate the result."
        )
        self._add_selection_arguments(parser)

    def handle(self, **kwargs):
        products = list(self.select_products(
            Product.objects.prefetch_related('collection'), **kwargs
        ))

        if products:
            for product in products:
                self.info("product %s/%s exists" % (
                    product.collection.identifier, product.identifier
                ))
        else:
            self.info("product %s does not exist" % kwargs['identifier'][0])

        result = bool(products)
        if kwargs['negate']:
            result = not result

        sys.exit(0 if result else 1)
