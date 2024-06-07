#-------------------------------------------------------------------------------
#
# Product management API
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

from logging import getLogger
from functools import wraps
from os.path import splitext, basename, abspath
from datetime import timedelta
from django.db import transaction
from vires.util import AttributeDict
from vires.exceptions import DataIntegrityError
from vires.time_util import format_datetime
from vires.models import Product, ProductLocation
from vires.metadata import METADATA_READERS
from vires.cdf_util import cdf_open
from .product_collection import get_product_collection
from .orbit_direction import (
    update_orbit_direction_tables,
    sync_orbit_direction_tables,
    rebuild_orbit_direction_tables,
)
from .conjunctions import (
    find_pair_collections,
    update_conjunctions_table,
    sync_conjunctions_table,
    rebuild_conjunctions_table,
)
from .cached_magnetic_model import (
    seed_product,
    flush_product_loose_file,
    get_model_cache_read_only_flag,
)

LOG_FORMAT = "product %s/%s %s"


def get_product_id(data_file):
    """ Get the product identifier. """
    return splitext(basename(data_file))[0]


def update_max_product_duration(collection, duration):
    """ Update collection maximum product duration attribute. """
    # round the duration up to the next whole second and add one extra second buffer
    duration = timedelta(
        days=duration.days,
        seconds=(duration.seconds + (2 if duration.microseconds > 0 else 1))
    )
    if duration > collection.max_product_duration:
        collection.max_product_duration = duration
        collection.save()


def read_product_metadata(data_file, product_type):
    """ Read metadata from product. """

    try:
        metadata_reader = METADATA_READERS[product_type.file_type]
    except KeyError:
        raise KeyError(
            f"Unsupported product file type {product_type.file_type}!"
        ) from None

    options = metadata_reader.extract_options(product_type)

    return metadata_reader.read(data_file, **options)


def get_product(collection_id, product_id):
    """ Get vires.models.Product object for the given collection and product
    identifiers or raises DoesNotExist exception.
    """
    return Product.objects.get(
        collection__identifier=collection_id, identifier=product_id,
    )


def find_products_by_location(data_file):
    """ Return query-set for products matched by the given data file location.
    """
    locations = ProductLocation.objects.filter(location=data_file)
    return Product.objects.filter(id__in=locations.values("product_id"))


def _log_registered_products(command):
    """ Product registration logging decorator. """

    @wraps(command)
    def wrapped_command(*args, **kawrags):
        logger = kawrags.get("logger") or getLogger(__name__)

        result = command(*args, **kawrags)

        collection_id = result.product.collection.identifier
        for product_id in result.deregistered:
            logger.info(LOG_FORMAT, collection_id, product_id, "de-registered")

        product_id = result.product.identifier
        if result.inserted:
            logger.info(LOG_FORMAT, collection_id, product_id, "registered")
        elif result.updated:
            logger.info(LOG_FORMAT, collection_id, product_id, "updated")
        else:
            logger.debug(LOG_FORMAT, collection_id, product_id, "ignored")

        return result

    return wrapped_command


def _postregisteration_cleanup(command):

    @wraps(command)
    def wrapped_command(*args, **kawrags):
        logger = kawrags.get("logger") or getLogger(__name__)

        result = command(*args, **kawrags)

        collection_id = result.product.collection.identifier
        if not get_model_cache_read_only_flag():
            for product_id in result.deregistered:
                flush_product_loose_file(collection_id, product_id, logger)

        return result

    return wrapped_command


@_postregisteration_cleanup
@_log_registered_products
def import_product(record, update_existing=True, **kwargs):
    """ Import product record.
    Options:
      record -      imported record dictionary, mandatory keys:
          identifier -  string, product identifier
          collection -  string, collection identifier
          begin_time -  datetime, acquisition/validity start
          end_time -    datetime, acquisition/validity end
          datasets -    dictionary, dataset definition
      update_existing -
                    if True the already existing product is updated
                    if False the already registered product is ignored
                    default True
      logger -      optional logger

    Returns:
      status - Attribute dictionary with the following keys:
          product -      the actual vires.models.Product object
          inserted -     boolean flag, True if a new product inserted
          updated -      boolean flag, True if an existing product updated

    Note that if the products has been neither inserted not updated then the
    existing already registered product has not been modified.

    Note that the import ignores any possible conflicts and time-overlaps
    """

    def _get_product(collection, identifier):
        try:
            product = collection.products.get(identifier=identifier)
            is_new = False
        except Product.DoesNotExist:
            product = Product(collection=collection, identifier=identifier)
            is_new = True
        return product, is_new

    def _save_product(product, data):
        product.begin_time = data["begin_time"]
        product.end_time = data["end_time"]
        product.datasets = data["datasets"]
        product.metadata = data["metadata"]
        product.save()
        update_max_product_duration(
            product.collection, product.end_time - product.begin_time
        )

    product_id = record["identifier"]
    collection = get_product_collection(record["collection"])
    product_type = record["product_type"]

    if product_type is not None and product_type != collection.type.identifier:
        raise ValueError("Collection product type mismatch!")

    product, inserted = _get_product(collection, product_id)

    updated = False
    if inserted or update_existing:
        with transaction.atomic():
            _save_product(product, record)
        updated = not inserted

    return AttributeDict(
        product=product,
        inserted=inserted,
        updated=updated,
        deregistered=[],
    )


def export_product(product):
    """ Export product record as an attribute dictionary. """
    return AttributeDict(
        identifier=product.identifier,
        begin_time=product.begin_time,
        end_time=product.end_time,
        created=product.created,
        updated=product.updated,
        collection=product.collection.identifier,
        product_type=product.collection.type.identifier,
        metadata=product.metadata,
        datasets=product.datasets,
    )


@_postregisteration_cleanup
@_log_registered_products
def register_product(collection, data_file, metadata,
                     update_existing=True, resolve_time_overlaps=True, **kwargs):
    """ Register new product.
    Options:
      collection -  vires.models.Collection object, collection in which the new
                    product should be inserted.
      data_file -   the product data file
      metadata -    dictionary of the product metadata. Required keys:
          identifier -  string, product identifier
          begin_time -  datetime acquisition/validity start
          end_time -    datetime, acquisition/validity end
      update_existing -
                    if True the already existing product is updated
                    if False the already registered product is ignored
                    default True
      resolve_time_overlaps -
                    if True then all time-overlapping products are de-registered
                    if False then the time-overlapping products are de-registered
                    default True
      logger -      optional logger

    Returns:
      status - Attribute dictionary with the following keys:
          product -      the actual vires.models.Product object
          inserted -     boolean flag, True if a new product inserted
          updated -      boolean flag, True if an existing product updated
          deregistered - list of the identifiers of the de-registered products

    Note that if the products has been neither inserted not updated then the
    existing already registered product has not been modified.
    """
    product_id = metadata["identifier"]
    begin_time = metadata["begin_time"]
    end_time = metadata["end_time"]

    with transaction.atomic():
        if resolve_time_overlaps:
            product, deregistered = _deregister_time_overlaps(
                collection, product_id, begin_time, end_time
            )
        else:
            product = _get_product_by_id(collection, product_id)
            deregistered = []

        inserted, updated = False, False
        if not product:
            product = _register_new_product(collection, data_file, **metadata)
            inserted = True
        elif update_existing:
            product = _update_existing_product(product, data_file, **metadata)
            updated = True

    return AttributeDict(
        product=product,
        inserted=inserted,
        updated=updated,
        deregistered=deregistered,
    )


def deregister_product(product, logger=None):
    """ De-register product.
    Options:
      product - given vires.models.Product object, product to be de-registered.
      logger -  optional logger
    Returns:
      None
    """
    if not logger:
        logger = getLogger(__name__)

    product_id = product.identifier
    collection_id = product.collection.identifier

    with transaction.atomic():
        _deregister_existing_product(product)

    logger.info(LOG_FORMAT, collection_id, product_id, "de-registered")

    if not get_model_cache_read_only_flag():
        flush_product_loose_file(collection_id, product_id, logger)


def execute_post_registration_actions(product, logger=None):
    """ Execute post-registration actions. """
    if not logger:
        logger = getLogger(__name__)

    if product.collection.metadata.get("calculateOrbitDirection"):
        _update_orbit_direction(product)

    if product.collection.metadata.get("calculateConjunctions"):
        for other_collection in find_pair_collections(product.collection):
            _update_conjunctions(product, other_collection)

    if (
        not get_model_cache_read_only_flag() and
        product.collection.cached_magnetic_models.exists()
    ):
        seed_product(product, logger=logger)


def _update_orbit_direction(product, logger=None):
    """ Update orbit directions from the given product. """
    local_logger = logger or getLogger(__name__)
    try:
        update_orbit_direction_tables(product, logger)
    except DataIntegrityError as error1:
        local_logger.warning(
            "Failed to update orbit direction table for %s product! %s",
            product.identifier, error1, exc_info=True
        )
        try:
            sync_orbit_direction_tables(product.collection, logger=logger)
        except DataIntegrityError as error2:
            local_logger.warning(
                "Failed to synchronize orbit direction table for %s collection!"
                " %s", product.collection.identifier, error2, exc_info=True
            )
            rebuild_orbit_direction_tables(product.collection, logger=logger)


def _update_conjunctions(product, other_collection, logger=None):
    """ Update conjunctions from the given product. """
    local_logger = logger or getLogger(__name__)
    try:
        update_conjunctions_table(product, other_collection, logger=logger)
    except DataIntegrityError as error1:
        local_logger.warning(
            "Failed to update conjunctions table for %s product! %s",
            product.identifier, error1, exc_info=True
        )
        try:
            sync_conjunctions_table(
                product.collection, other_collection, logger=logger
            )
        except DataIntegrityError as error2:
            local_logger.warning(
                "Failed to synchronize conjunctions table for %s collection!"
                " %s", product.collection.identifier, error2, exc_info=True
            )
            rebuild_conjunctions_table(
                product.collection, other_collection, logger=logger
            )


def _deregister_existing_product(product):
    product.delete()


def _register_new_product(collection, data_file, identifier, **metadata):
    return _set_product(
        Product(identifier=identifier, collection=collection),
        data_file, **metadata
    )


def _update_existing_product(product, data_file, **metadata):
    return _set_product(product, data_file, **metadata)


def _set_product(product, data_file, **metadata):
    """ Update and save product. """
    product.begin_time = metadata["begin_time"]
    product.end_time = metadata["end_time"]
    product.datasets = _get_datasets(
        data_file, product.collection.type, metadata
    )
    product.metadata = _exlude_dict_keys(metadata, excluded_keys=[
        "begin_time",
        "end_time",
        "datasets",
    ])
    product.save()
    update_max_product_duration(
        product.collection, product.end_time - product.begin_time
    )
    return product


def _exlude_dict_keys(data, excluded_keys):
    excluded_keys = set(excluded_keys)
    return {
        key: value
        for key, value in data.items()
        if key not in excluded_keys
    }


def _get_datasets(data_file, product_type, metadata):
    datasets = _get_datasets_from_product_type(abspath(data_file), product_type)
    if "datasets" in metadata:
        datasets.update(_get_datasets_from_datasets_metadata(
            abspath(data_file), metadata["datasets"]
        ))
    return datasets


def _get_datasets_from_datasets_metadata(data_file, datasets):
    def _sanitize(record):
        return {
            key: value for key, value in record.items() if value is not None
        }
    return {
        name: _sanitize({
            "location": data_file,
            "indexRange": metadata.get("index_range"),
            "beginTime": format_datetime(metadata.get("begin_time")),
            "endTime": format_datetime(metadata.get("end_time")),
            "geographicLocation": metadata.get("location"),
        }) for name, metadata in datasets.items()
    }


def _get_datasets_from_product_type(data_file, product_type):
    datasets = {
        name: {
            "location": data_file,
        } for name in product_type.definition["datasets"]
    }
    for name in product_type.definition.get("unsortedDatasets") or []:
        (datasets.get(name) or {})["isSorted"] = False
    return datasets


def _deregister_time_overlaps(collection, product_id, begin_time, end_time):
    matched_product = None
    deregistered = []
    for product in _find_product_time_overlap(collection, begin_time, end_time):
        if product.identifier != product_id:
            _deregister_existing_product(product)
            deregistered.append(product.identifier)
        else:
            matched_product = product
    return matched_product, deregistered


def _get_product_by_id(collection, product_id):
    try:
        return collection.products.get(identifier=product_id)
    except Product.DoesNotExist:
        return None


def _find_product_time_overlap(collection, begin_time, end_time):
    return collection.products.filter(
        begin_time__lte=end_time,
        begin_time__gte=(begin_time - collection.max_product_duration),
        end_time__gte=begin_time
    )
