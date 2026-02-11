#-------------------------------------------------------------------------------
#
# Collect summary of the state of magnetic models cache
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023-2024 EOX IT Services GmbH
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

from vires.models import CachedMagneticModel, ProductCollection
from vires.util_multiprocessing import N_CPU, MultiProcessStreamExecutor
from ...api.cached_magnetic_model import collect_collection_cache_stats
from .common import CachedMagneticModelsSubcommand


class StatsCachedMagneticModelsSubcommand(CachedMagneticModelsSubcommand):
    name = "stats"
    help = "Collect statistic of the state of the magnetic models cache."

    ALIGNMENT = "  "

    def add_arguments(self, parser):
        self._add_collection_selection_arguments(parser)
        parser.add_argument(
            "-n", "--number-of-worker-processes",
            type=int,
            dest="n_proc",
            default=N_CPU,
            help=(
                "Number of worker processes. Defaults to the actual number of "
                f"CPU cores ({N_CPU})."
            ),
        )
        parser.add_argument(
            "--issues-only", dest="print_issues_only",
            action="store_true", default=False, help=(
                "Print output only when issues were detected."
            )
        )

    def handle(self, **kwargs):
        models = self.select_collections(
            CachedMagneticModel.objects.order_by("collection", "name"), **kwargs
        )

        collections = list(
            ProductCollection.objects
            .filter(id__in=models.values_list("collection", flat=True))
            .order_by("identifier")
            .distinct()
        )

        model_names = set(models.values_list("name", flat=True))

        n_workers = max(1, kwargs["n_proc"])
        print_issues_only = kwargs["print_issues_only"]

        executor = (
            MultiProcessStreamExecutor(n_workers) if n_workers > 1 else None
        )

        for collection in collections:
            stats = collect_collection_cache_stats(
                collection=collection,
                model_names=model_names,
                logger=self.logger,
                executor=executor,
            )
            if not (
                print_issues_only
                and stats["collection"]["synced"]
                and stats["collection"]["clean"]
            ):
                self.print_collection_stats(collection, stats)

    def print_collection_stats(self, collection, stats):

        collection_stats = stats["collection"]
        collection_status = [
            ("NOT ", "")[collection_stats["synced"]] + "SYNCED",
            ("NOT ", "")[collection_stats["clean"]] + "CLEAN",
        ]

        print()
        print(f"{collection.identifier}: [{','.join(collection_status)}]")
        self.print_file_stats(stats["files"], alignment=self.ALIGNMENT)
        print(f"{self.ALIGNMENT}models:")
        for model_name, model_stats in stats["models"].items():
            print(f"{self.ALIGNMENT*2}{model_name}:")
            self.print_model_stats(model_stats, alignment=self.ALIGNMENT*3)

    @staticmethod
    def print_model_stats(model_stats, alignment=""):
        print(f"{alignment}seeded files:           {model_stats['seeded']}")
        if model_stats['missing'] > 0:
            print(f"{alignment}missing seeded files:   {model_stats['missing']}")
        if model_stats['obsolete'] > 0:
            print(f"{alignment}obsolete seeded files:  {model_stats['obsolete']}")
        if model_stats['loose'] > 0:
            print(f"{alignment}loose seeded files:     {model_stats['loose']}")

    @staticmethod
    def print_file_stats(file_stats, alignment=""):
        print(f"{alignment}source products: {file_stats['product_count']}")
        print(f"{alignment}cache files:     {file_stats['file_count']}")
        if file_stats['missing_file_count'] > 0:
            print(f"{alignment}missing files:   {file_stats['missing_file_count']}")
        if file_stats['loose_file_count'] > 0:
            print(f"{alignment}loose files:     {file_stats['loose_file_count']}")
        if file_stats['missing_variables_file_count'] > 0:
            print(f"{alignment}files with missing variables: {file_stats['missing_variables_file_count']}")
