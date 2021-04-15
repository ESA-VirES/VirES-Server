#-------------------------------------------------------------------------------
#
# product management - common utilities
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

from os.path import isfile
from vires.models import ProductLocation
from .._common import Subcommand, time_spec


class ProductSelectionSubcommand(Subcommand):
    """ Product selection subcommand. """

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
        self._add_selection_arguments(parser)

    def _add_selection_arguments(self, parser):
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
        parser.add_argument(
            "-l", "--location", "--product-location",
            dest="product_location", action="store_true", default=False,
            help=(
                "Select products by the data file location rather than "
                "by the product identifier."
            )
        ),
        parser.add_argument(
            "--after", type=time_spec, required=False,
            help="Select products after the given date."
        )
        parser.add_argument(
            "--before", type=time_spec, required=False,
            help="Select products before the given date."
        )
        parser.add_argument(
            "--created-after", type=time_spec, required=False,
            help="Select products whose record has been created after the given date."
        )
        parser.add_argument(
            "--created-before", type=time_spec, required=False,
            help="Select products whose record has been created before the given date."
        )
        parser.add_argument(
            "--updated-after", type=time_spec, required=False,
            help="Select products whose record has been updated after the given date."
        )
        parser.add_argument(
            "--updated-before", type=time_spec, required=False,
            help="Select products whose record has been updated before the given date."
        )
        parser.add_argument(
            "--invalid-only", dest="invalid_only", action="store_true",
            default=False, help="Select invalid products missing a data-file."
        )

    def select_products(self, query, **kwargs):
        """ Select products based on the CLI parameters. """
        if kwargs['after']:
            query = query.filter(begin_time__gte=kwargs['after'])

        if kwargs['before']:
            query = query.filter(end_time__lt=kwargs['before'])

        if kwargs['created_after']:
            query = query.filter(created__gte=kwargs['created_after'])

        if kwargs['created_before']:
            query = query.filter(created__lt=kwargs['created_before'])

        if kwargs['updated_after']:
            query = query.filter(updated__gte=kwargs['updated_after'])

        if kwargs['updated_before']:
            query = query.filter(updated__lt=kwargs['updated_before'])

        product_types = set(kwargs['product_type'] or [])
        if product_types:
            query = query.filter(collection__type__identifier__in=product_types)

        product_collections = set(kwargs['product_collection'] or [])
        if product_collections:
            query = query.filter(collection__identifier__in=product_collections)

        query = self._select_products_by_id(query, **kwargs)

        if kwargs['invalid_only']:
            query = filter_invalid(query, self.logger)

        return query

    def _select_products_by_id(self, query, **kwargs):
        identifiers = set(kwargs['identifier'])
        if identifiers:
            query = self._select_listed_product(query, identifiers, **kwargs)
        return query

    def _select_listed_product(self, query, identifiers, **kwargs):
        if kwargs['product_location']:
            subquery = ProductLocation.objects.filter(location__in=identifiers)
            query = query.filter(id__in=subquery.values('product_id'))
        else:
            query = query.filter(identifier__in=identifiers)
        return query


class ProductSelectionSubcommandProtected(ProductSelectionSubcommand):
    """ Product selection subcommand requiring --all if no id given."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all products."
        )

    def _select_products_by_id(self, query, **kwargs):
        identifiers = set(kwargs['identifier'])
        if identifiers or not (kwargs['select_all'] or kwargs['invalid_only']):
            query = self._select_listed_product(query, identifiers, **kwargs)
            if not identifiers:
                self.warning(
                    "No identifier selected and no product will be removed. "
                    "Use the --all option to remove all matched items."
                )
        return query


def filter_invalid(products, logger=None):
    """ Filter invalid products. """
    for product in products:
        if is_invalid(product, logger):
            yield product


def is_invalid(product, logger=None):
    """ Return true is products is invalid. """
    for dataset in product.datasets.values():
        location = dataset.get('location')
        if location and not isfile(location):
            logger.warning(
                "Invalid product %s detected! "
                "File %s does not exist!", product.identifier, location
            )
            return True
    return False
