#-------------------------------------------------------------------------------
#
# cached magnetic models management - common utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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


class CachedMagneticModelsSubcommand(Subcommand):
    """ Cached magnetic models subcommand. """

    def add_arguments(self, parser):
        self._add_model_names_arguments(parser)
        self._add_collection_selection_arguments(parser)

    def _add_model_names_arguments(self, parser):
        parser.add_argument("name", nargs="*")

    def _add_collection_selection_arguments(self, parser):
        parser.add_argument(
            "-t", "--product-type", dest="product_type", action="append", help=(
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
            "-m", "--mission", dest="mission", action="append", help=(
                "Optional filter on the mission type. "
                "Multiple missions are allowed."
            )
        )
        parser.add_argument(
            "-s", "--spacecraft", dest="spacecraft", action="append", help=(
                "Optional filter on the spacecraft identifier. "
                "Multiple spacecrafts are allowed."
            )
        )

    def select_collections(self, query, **kwargs):
        product_types = set(kwargs["product_type"] or [])
        if product_types:
            query = query.filter(collection__type__identifier__in=product_types)

        product_collections = set(kwargs["product_collection"] or [])
        if product_collections:
            query = query.filter(collection__identifier__in=product_collections)

        missions = set(kwargs["mission"] or [])
        if missions:
            query = query.filter(
                collection__spacecraft__mission__in=missions,
            )

        spacecrafts = set(kwargs["spacecraft"] or [])
        if spacecrafts:
            query = query.filter(
                collection__spacecraft__spacecraft__in=spacecrafts,
            )

        return query

    def select_models(self, query, **kwargs):
        """ Select cached models based on the CLI parameters. """
        query = self.select_collections(query, **kwargs)
        query = self._select_models_by_name(query, **kwargs)
        return query

    def _select_models_by_name(self, query, **kwargs):
        names = set(kwargs["name"])
        if names:
            query = query.filter(name__in=names)
        return query


class CachedMagneticModelsProtectedSubcommand(CachedMagneticModelsSubcommand):
    """ Cached magnetic models subcommand requiring --all if no id given. """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all models."
        )

    def _select_models_by_name(self, query, **kwargs):
        names = set(kwargs["name"])
        if names or not kwargs["select_all"]:
            query = query.filter(name__in=names)
            if not names:
                self.warning(
                    "No model identifier selected and no will be taken. "
                    "Use the --all option to select all models."
                )
        return query


class ProductFilter:
    """ Product filter. """

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "-i", "--product-id", dest="product_id", action="append", help=(
                "Optional product identifier. Multiple identifiers are allowed."
            )
        )
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

    @classmethod
    def create_product_filter(cls, **kwargs):

        def _product_filter(query):
            if kwargs["after"]:
                query = query.filter(begin_time__gte=kwargs["after"])

            if kwargs["before"]:
                query = query.filter(end_time__lt=kwargs["before"])

            if kwargs["created_after"]:
                query = query.filter(created__gte=kwargs["created_after"])

            if kwargs["created_before"]:
                query = query.filter(created__lt=kwargs["created_before"])

            if kwargs["updated_after"]:
                query = query.filter(updated__gte=kwargs["updated_after"])

            if kwargs["updated_before"]:
                query = query.filter(updated__lt=kwargs["updated_before"])

            product_ids = set(kwargs.get("product_id") or [])
            if product_ids:
                query = query.filter(identifier__in=product_ids)

            return query

        return _product_filter
