#-------------------------------------------------------------------------------
#
# Update orbit direction cached product for selected products.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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
from traceback import print_exc
from vires.util import unique
from .._common import Subcommand
from .common import (
    DataIntegrityError, Counter, find_product_by_id,
    update_orbit_direction_tables, sync_orbit_direction_tables,
)


class UpdateOrbitDirectionSubcommand(Subcommand):
    name = "update"
    help = """ Update orbit direction tables from the listed products. """

    def add_arguments(self, parser):
        parser.add_argument(
            "product-identifier", nargs="*",
            help="Identifier of the source product to update OD tables."
        )

    def handle(self, **kwargs):
        counter = Counter()
        self.update_from_products(
            counter, kwargs.pop('product-identifier'), **kwargs
        )
        counter.print_report(self.info)


    def update_from_products(self, counter, product_ids, **kwargs):
        """ update orbit direction table from a list of products. """

        for product_id in unique(product_ids):

            product = find_product_by_id(product_id)
            if product is None:
                self.error(
                    "Processing of %s failed! Product not found in any allowed "
                    "collections!", product_id,
                )
                counter.increment_failed()
                counter.increment()
                continue

            try:
                processed = update_orbit_direction_tables(product)
            except DataIntegrityError as error:
                self.warning(str(error))
                sync_orbit_direction_tables(
                    product.collection, logger=self, counter=counter
                )
            except Exception as error:
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Processing of %s failed! Reason: %s", product_id, error
                )
                counter.increment_failed()
            else:
                if processed:
                    counter.increment_processed()
                    self.info(
                        "%s orbit direction lookup table extracted", product_id
                    )
                else:
                    counter.increment_skipped()
                    self.info(
                        "%s orbit direction lookup table extraction skipped",
                        product_id
                    )
            finally:
                counter.increment()
