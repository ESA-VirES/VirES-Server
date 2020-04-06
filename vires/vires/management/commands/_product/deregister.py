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
from .common import ProductSelectionSubcommandProtected


class DeregisterProductSubcommand(ProductSelectionSubcommandProtected):
    name = "deregister"
    help = "Deregister products."

    def handle(self, **kwargs):
        products = self.select_products(
            Product.objects.prefetch_related('collection'), **kwargs
        )
        self.deregister_products(products, **kwargs)

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
                    "Failed to de-register product %s from collection %s! %s",
                    identifier, collection_id, error
                )
            else:
                removed_count += 1
                self.info(
                    "product %s/%s de-registered", collection_id, identifier,
                    log=True
                )
            finally:
                total_count += 1

        if removed_count:
            self.info(
                "%d of %d matched product%s de-registered.",
                removed_count, total_count, "s" if removed_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d matched product%s failed to be de-registered.",
                failed_count, total_count, "s" if failed_count > 1 else ""
            )

        sys.exit(failed_count)
