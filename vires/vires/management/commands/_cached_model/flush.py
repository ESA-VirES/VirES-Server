#-------------------------------------------------------------------------------
#
# Flush magnetic models cache
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

from django.core.management.base import CommandError
from vires.models import CachedMagneticModel, ProductCollection
from vires.util_multiprocessing import N_CPU, MultiProcessStreamExecutor
from ...api.cached_magnetic_model import (
   get_model_cache_read_only_flag,
   flush_collection_loose_files,
   flush_collection,
)
from .common import CachedMagneticModelsProtectedSubcommand, ProductFilter


class FlushCachedMagneticModelsSubcommand(CachedMagneticModelsProtectedSubcommand):
    name = "flush"
    help = (
        "Flush magnetic models cache. By default the flush removes: 1) "
        "all loose cache files and 2) all obsolete or loose models."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        ProductFilter.add_arguments(parser)
        parser.add_argument(
            "-f", "--force", dest="force_flush", action="store_true",
            default=False, help=(
                "Force flushing of all cached models, including, non-obsolete "
                "ones."
            ),
        )
        parser.add_argument(
            "-r", "--remove-empty", dest="remove_empty", action="store_true",
            default=False, help="Remove empty cache files.",
        )
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

    def handle(self, **kwargs):

        if get_model_cache_read_only_flag():
            raise CommandError(
                "Operation not permitted for read-only model cache!"
            )

        models = self.select_models(
            CachedMagneticModel.objects.order_by("collection", "name"), **kwargs
        )

        collections = list(
            ProductCollection.objects
            .filter(id__in=models.values_list("collection", flat=True))
            .order_by("identifier")
            .distinct()
        )

        model_names = set(models.values_list("name", flat=True))

        product_filter = ProductFilter.create_product_filter(**kwargs)

        n_workers = max(1, kwargs["n_proc"])

        executor = (
            MultiProcessStreamExecutor(n_workers) if n_workers > 1 else None
        )

        for collection in collections:
            flush_collection_loose_files(
                collection=collection,
                logger=self.logger,
            )
            flush_collection(
                collection=collection,
                model_names=model_names,
                product_filter=product_filter,
                force_flush=kwargs["force_flush"],
                remove_empty_files=kwargs["remove_empty"],
                flush_nonlisted_models=(
                    not kwargs["name"] and kwargs["select_all"]
                ),
                logger=self.logger,
                executor=executor,
            )
