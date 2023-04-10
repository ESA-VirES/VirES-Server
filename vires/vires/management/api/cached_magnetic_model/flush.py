#-------------------------------------------------------------------------------
#
# Cached magnetic models management API - cache flushing subroutines
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
from vires.cdf_util import cdf_open
from .common import (
    get_collection_model_cache_directory,
    get_product_model_cache_file,
    select_products,
    select_models,
    init_directory,
    remove_file,
    rename_file,
    copy_file,
    list_cache_files,
    get_temp_cache_file,
)
from .seed import _extract_model_sources
from .file_format import (
    remove_cache_file,
    read_model_cache_description,
    read_sources,
    write_sources,
    append_log_record,
    remove_model_data,
)


def flush_product_loose_file(collection_id, product_id, logger):
    """ Remove loose file for the given product. """
    cache_dir = get_collection_model_cache_directory(collection_id)
    cache_file = get_product_model_cache_file(cache_dir, product_id)
    remove_cache_file(cache_file, logger)


def flush_collection_loose_files(collection, logger=None):
    """ Remove all loose files from a collection. """
    logger = logger or getLogger(__name__)
    cache_dir = get_collection_model_cache_directory(collection.identifier)

    cache_file_ids = set(list_cache_files(cache_dir))
    for product in collection.products.all():
        try:
            cache_file_ids.remove(product.identifier)
        except KeyError:
            pass

    for cahe_file_id in cache_file_ids:
        cache_file = get_product_model_cache_file(cache_dir, cahe_file_id)
        remove_cache_file(cache_file, logger)


def flush_collection(collection, model_names=None, product_filter=None,
                     force_flush=False, remove_empty_files=False,
                     flush_nonlisted_models=False, logger=None):
    """ Flush cached models for the given collection. """
    logger = logger or getLogger(__name__)
    models = select_models(collection, model_names)

    cache_options = collection.metadata.get("cachedMagneticModels") or {}
    cache_dir = get_collection_model_cache_directory(collection.identifier)
    init_directory(cache_dir, logger)

    for product in select_products(collection, product_filter):
        cache_file = get_product_model_cache_file(cache_dir, product.identifier)

        _flush_product(
            product, cache_file, models,
            options=cache_options,
            force_flush=force_flush,
            flush_nonlisted_models=flush_nonlisted_models,
            remove_empty_file=remove_empty_files,
            logger=logger
        )


def _flush_product(product, cache_file, models, options, force_flush,
                  remove_empty_file, flush_nonlisted_models, logger):
    """ Flush magnetic model cache for one product. """
    del options

    tmp_cache_file = get_temp_cache_file(cache_file)

    cache_description = read_model_cache_description(cache_file, logger)

    if cache_description is None:
        # cache file does not exist => nothing to be done
        return

    flushed_model_names, retained_model_names = _get_listed_and_retained_models(
        product, cache_description, models, force_flush, flush_nonlisted_models
    )

    if remove_empty_file and not retained_model_names:
        remove_cache_file(cache_file, logger)
        return

    if not flushed_model_names:
        return

    try:
        copy_file(cache_file, tmp_cache_file)

        _flush_models(product, tmp_cache_file, flushed_model_names, logger)

        rename_file(tmp_cache_file, cache_file)

    finally:
        remove_file(tmp_cache_file)


def _flush_models(product, cache_file, model_names, logger):
    with cdf_open(cache_file, "w") as cdf:
        for model_name in model_names:
            _flush_model(cdf, model_name)
            logger.info(
                "Flushed magnetic model cache for %s/%s/%s",
                product.collection.identifier,
                product.identifier,
                model_name,
            )


def _flush_model(cdf, model_name):
    remove_model_data(cdf, model_name)
    _update_attributes(cdf, model_name)


def _update_attributes(cdf, model_name):
    write_sources(cdf, [
        *(
            (name, *source) for name, *source in read_sources(cdf)
            if name != model_name
        ),
    ])
    append_log_record(cdf, f"flushing {model_name}")


def _get_listed_and_retained_models(product, cache_description, models,
                                    force_flush, flush_nonlisted_models):
    def _is_seeded(model):
        return model.name in cache_description

    def _is_obsolete(model):
        return (
            cache_description[model.name] !=
            _extract_model_sources(model, product)
        )

    if force_flush:
        flushed_model_names = [
            model.name for model in models
            if _is_seeded(model)
        ]

    else:
        flushed_model_names = [
            model.name for model in models
            if _is_seeded(model) and _is_obsolete(model)
        ]

    if flush_nonlisted_models:
        flushed_model_names.extend(
            _list_loose_models(models, cache_description)
        )

    retained_model_names = list(
        set(cache_description) - set(flushed_model_names)
    )

    return flushed_model_names, retained_model_names


def _list_loose_models(models, cache_description):
    listed_model_names = set(model.name for model in models)
    for model_name in cache_description:
        if model_name not in listed_model_names:
            yield model_name
