#-------------------------------------------------------------------------------
#
# Cached magnetic models management API - collect cache status
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

from logging import getLogger
from .common import (
    select_products,
    select_models,
    get_collection_model_cache_directory,
    get_product_model_cache_file,
    list_cache_files,
)
from .file_format import read_model_cache_description
from .model import extract_model_sources_datetime, parse_source_model


def collect_collection_cache_stats(collection, model_names=None, logger=None):
    """ Collect statistics for the given magnetic model cache collection. """
    logger = logger or getLogger(__name__)

    models = select_models(collection, model_names)
    cache_dir = get_collection_model_cache_directory(collection.identifier)
    existing_cache_files = set(list_cache_files(cache_dir))
    product_selection = select_products(collection)

    collection_stats = {
        "clean": True,
        "synced": True,
    }

    file_stats = {
        "file_count": len(existing_cache_files),
        "product_count": product_selection.count(),
        "missing_file_count": 0,
        "loose_file_count": 0,
    }

    def _new_model_stats():
        return {
            "seeded": 0,
            "obsolete": 0,
            "missing": 0,
            "loose": 0,
        }

    model_stats = {
        model.name: _new_model_stats()
        for model in models
    }

    for product in product_selection:
        cache_file = get_product_model_cache_file(cache_dir, product.identifier)
        try:
            existing_cache_files.remove(product.identifier)
        except KeyError:
            file_stats["missing_file_count"] += 1
            collection_stats["synced"] = False
            continue

        cache_description = read_model_cache_description(cache_file, logger) or {}
        model_list = set(cache_description)

        for model in models:
            single_model_stats = model_stats[model.name]
            try:
                model_list.remove(model.name)
                single_model_stats["seeded"] += 1
            except KeyError:
                single_model_stats["missing"] += 1
                collection_stats["synced"] = False
                continue

            model_sources = _extract_model_sources(model, product)
            cache_sources = cache_description[model.name]

            if model_sources != cache_sources:
                single_model_stats["obsolete"] += 1
                collection_stats["clean"] = False

        for loose_model in model_list:
            if loose_model not in model_stats:
                model_stats[loose_model] = _new_model_stats()
            single_model_stats = model_stats[loose_model]
            single_model_stats["seeded"] += 1
            single_model_stats["loose"] += 1
            collection_stats["clean"] = False

    file_stats["loose_file_count"] = len(existing_cache_files)
    if file_stats["loose_file_count"] > 0:
        collection_stats["clean"] = False

    return {
        "collection": collection_stats,
        "files": file_stats,
        "models": model_stats,
    }


def _extract_model_sources(db_model, product):
    return set(
        extract_model_sources_datetime(
            parse_source_model(db_model.expression),
            product.begin_time,
            product.end_time,
        )
    )
