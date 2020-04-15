#-------------------------------------------------------------------------------
#
# Update cached product
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

from django.core.management.base import CommandError
from vires.management.api.cached_product import (
    CACHED_PRODUCTS, update_cached_product,
)
from .._common import Subcommand


class UpdateCachedProductSubcommand(Subcommand):
    name = "update"
    help = """ Update cached product. """

    def add_arguments(self, parser):
        parser.add_argument(
            "product_type", help="Product type",
            choices=list(sorted(CACHED_PRODUCTS)),
        )
        parser.add_argument(
            "source", nargs="+", help="Source filename or URL."
        )

    def handle(self, **kwargs):
        product_type = kwargs['product_type']
        sources = kwargs['source']

        try:
            update_cached_product(product_type, *sources, logger=self.logger)
        except Exception as error:
            raise CommandError(
                "Failed to update cached file %s! %s" % (product_type, error)
            )
