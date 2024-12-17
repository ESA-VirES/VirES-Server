#-------------------------------------------------------------------------------
#
# Cached magnetic models management API - cache seeding subroutines
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

from logging import getLogger
from vires.cdf_util import cdf_open
from vires.time_util import mjd2000_to_datetime
from .common import (
    get_collection_model_cache_directory,
    get_product_model_cache_file,
    select_products,
    select_models,
    init_directory,
    remove_file,
    rename_file,
    copy_file,
    get_temp_cache_file,
)
from .model import (
    parse_source_model,
    extract_model_sources_and_time_ranges_mjd2000,
    extract_model_sources_datetime,
)
from .file_format import (
    init_cache_file,
    read_model_cache_description,
    read_sources_with_time_ranges,
    write_sources_with_time_ranges,
    append_log_record,
    read_times_and_locations_data,
    write_model_data,
    save_options,
    copy_missing_variables,
)


def seed_collection(collection, model_names=None, product_filter=None,
                    force_reseed=False, logger=None, executor=None):
    """ Seed cached models for the given collection. """
    logger = logger or getLogger(__name__)
    models = select_models(collection, model_names)

    if not models:
        return

    cache_options = collection.metadata.get("cachedMagneticModels") or {}
    cache_dir = get_collection_model_cache_directory(collection.identifier)
    init_directory(cache_dir, logger)

    def _list_cache_files():
        for product in select_products(collection, product_filter):
            cache_file = get_product_model_cache_file(cache_dir, product.identifier)
            yield product, cache_file

    def _process_results(items):
        for _ in items:
            pass

    def _seed_cache(records):
        for product, cache_file in records:
            yield _seed_product(
                product, cache_file, models, options=cache_options,
                force_reseed=force_reseed, logger=logger
            )

    def _seed_cache_with_executor(executor, cache_files):

        def _submit_job(submit, record):
            product, cache_file = record
            return submit(
                _seed_product,
                product, cache_file, models, options=cache_options,
                force_reseed=force_reseed, logger=logger
            )

        def _handle_result(future, record):
            del record
            try:
                return future.result()
            except Exception as error:
                logger.exception("Failed to read cache file description! filename=%s", cache_file)
                return None

        return executor(cache_files, _submit_job, _handle_result)

    cache_files = _list_cache_files()
    results = (
        _seed_cache_with_executor(executor, cache_files)
        if executor else _seed_cache(cache_files)
    )
    return _process_results(results)


def seed_product(product, model_names=None, force_reseed=False, logger=None):
    """ Seed cached models for the given product. """
    logger = logger or getLogger(__name__)
    models = select_models(product.collection, model_names)

    if not models:
        return

    cache_options = product.collection.metadata.get("cachedMagneticModels") or {}
    cache_dir = get_collection_model_cache_directory(product.collection.identifier)
    init_directory(cache_dir, logger)

    cache_file = get_product_model_cache_file(cache_dir, product.identifier)
    _seed_product(
        product, cache_file, models, options=cache_options,
        force_reseed=force_reseed, logger=logger,
    )


def _seed_product(product, cache_file, models, options, force_reseed, logger):
    """ Seed magnetic model cache for one product. """

    tmp_cache_file = get_temp_cache_file(cache_file)

    (
        cache_description, has_missing_variables,
    ) = read_model_cache_description(cache_file, logger)

    create_new_cache_file = cache_description is None
    if create_new_cache_file:
        cache_description = {}

    def _is_not_seeded(model):
        return model.name not in cache_description

    def _is_obsolete(model):
        return (
            cache_description[model.name] !=
            _extract_model_sources(model, product)
        )

    seeded_models = models if force_reseed else [
        model for model in models
        if _is_not_seeded(model) or _is_obsolete(model)
    ]

    if not seeded_models and not has_missing_variables:
        return

    try:
        if create_new_cache_file:
            init_cache_file(cache_file, product, logger)

        copy_file(cache_file, tmp_cache_file)

        _seed_models(product, tmp_cache_file, seeded_models, options, logger)

        rename_file(tmp_cache_file, cache_file)

    finally:
        remove_file(tmp_cache_file)


def _seed_models(product, cache_file, models, options, logger):

    product_file = product.get_location(
        product.collection.type.default_dataset_id
    )

    with cdf_open(cache_file, "w") as cdf:

        save_options(cdf, options)

        copy_missing_variables(cdf, product_file)

        data = read_times_and_locations_data(cdf)

        for model in models:
            _seed_model(cdf, model, data, options)
            logger.info(
                "Seeded magnetic model cache for %s/%s/%s",
                product.collection.identifier,
                product.identifier,
                model.name,
            )


def _seed_model(cdf, db_model, data, options):
    del options
    model = parse_source_model(db_model.expression)
    b_nec = model.model.eval(**data, scale=[1, 1, -1])
    write_model_data(cdf, db_model.name, b_nec)
    _update_attributes(cdf, db_model.name, model, data)


def _update_attributes(cdf, model_name, model, data):

    def _extract_sources():
        if data["time"].size == 0:
            return
        start, end = data["time"][[0, -1]] # assuming sorted values
        sources = extract_model_sources_and_time_ranges_mjd2000(model, start, end)
        for name, source_start, source_end in sources:
            yield (
                name,
                mjd2000_to_datetime(source_start),
                mjd2000_to_datetime(source_end),
            )

    new_sources = list(_extract_sources())
    write_sources_with_time_ranges(cdf, [
        *(
            (name, *source) for name, *source
            in read_sources_with_time_ranges(cdf)
            if name != model_name
        ),
        *(
            (model_name, *source) for source in new_sources
        ),
    ])

    formatted_sources = ", ".join(name for name, *rest in new_sources)
    append_log_record(cdf, f"seeding {model_name} from {formatted_sources}")


def _extract_model_sources(db_model, product):
    return set(
        extract_model_sources_datetime(
            parse_source_model(db_model.expression),
            product.begin_time,
            product.end_time,
        )
    )
