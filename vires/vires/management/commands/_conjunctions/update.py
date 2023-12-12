#-------------------------------------------------------------------------------
#
# Update conjunction table from selected orbit products.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
#pylint: disable=missing-docstring

import sys
from vires.util import unique
from vires.management.api.conjunctions import (
    update_conjunctions_tables,
    find_products_by_id,
)
from .._common import Subcommand
from .common import Counter


class UpdateConjunctionsSubcommand(Subcommand):
    name = "update"
    help = """ Update conjunction table from the listed products. """

    def add_arguments(self, parser):
        parser.add_argument(
            "product-identifier", nargs="*",
            help="Identifier of the source product to update the table."
        )

    def handle(self, **kwargs):
        counter = Counter()
        self.update_from_products(
            counter, kwargs.pop('product-identifier'), **kwargs
        )
        counter.print_report(self.info)
        sys.exit(counter.failed)


    def update_from_products(self, counter, product_ids, **kwargs):
        """ update conjunctions table from a list of products. """

        for product_id in unique(product_ids):

            collection_counter = 0

            for product in find_products_by_id(product_id):
                collection_counter += 1

                self.log = True
                update_conjunctions_tables(
                    product, logger=self, counter=counter
                )
                self.log = False

            if collection_counter < 1:
                self.error(
                    "Processing of %s failed! Product not found in any "
                    "applicable collection!", product_id,
                )
                counter.failed += 1
                counter.total += 1
