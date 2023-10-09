#-------------------------------------------------------------------------------
#
# Orbit direction lookup tables management API
#
# Authors: Martin Paces martin.paces@eox.at
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
#pylint: disable=missing-docstring,broad-except

from logging import getLogger
from collections import namedtuple
from vires.time_util import naive_to_utc
from vires.models import ProductCollection, Product
from vires.exceptions import DataIntegrityError
from vires.orbit_direction import OrbitDirectionTables
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    ORBIT_DIRECTION_GEO_FILE, ORBIT_DIRECTION_MAG_FILE,
    OD_THRESHOLDS_DEFAULT, OD_THRESHOLDS,
)


def sync_orbit_direction_tables(collection, logger=None, counter=None):
    """ Sync orbit direction lookup tables for the given collection. """

    if not logger:
        logger = getLogger(__name__)

    if not counter:
        counter = Counter()

    thresholds = get_orbit_direction_thresholds(*collection.spacecraft_tuple)

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(*collection.spacecraft_tuple, collection.grade),
        **thresholds, logger=logger
    )

    logger.info(
        "Synchronizing orbit direction lookup tables for collection "
        "%s ...", collection.identifier
    )

    for product_id in od_tables.products.difference(
        item.id for item in iter_product_items(collection)
    ):
        od_tables.remove(product_id)
        counter.removed += 1

    for item in iter_product_items(collection):
        counter.total += 1

        processed = _update_orbit_direction_tables(
            od_tables, collection, item, **thresholds,
        )

        if processed:
            counter.processed += 1
        else:
            counter.skipped += 1

    if od_tables.changed:
        od_tables.save()

    return counter


def rebuild_orbit_direction_tables(collection, logger=None, counter=None):
    """ Re-build orbit direction lookup tables for the given collection. """

    if not logger:
        logger = getLogger(__name__)

    if not counter:
        counter = Counter()

    thresholds = get_orbit_direction_thresholds(*collection.spacecraft_tuple)

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(*collection.spacecraft_tuple, collection.grade),
        **thresholds, reset=True, logger=logger
    )

    if collection is None:
        logger.warning(
            "Collection %s does not exist! Blank orbit "
            "direction lookup tables will be saved.", collection.identifier
        )
        od_tables.save()
        return counter

    logger.info(
        "Rebuilding orbit direction lookup tables for collection "
        "%s ...", collection.identifier
    )

    last_item = None
    max_product_gap = thresholds["max_product_gap"]

    for item in iter_product_items(collection):
        counter.total += 1

        if item.start > item.end:
            raise ValueError(f"Product end before start! {item.id}")

        if not last_item or last_item.start < item.start:
            use_last_item = (
                last_item and (item.start - last_item.end) < max_product_gap
            )

            od_tables.update(
                item.id,
                item.filename,
                last_item.id if use_last_item else None,
                last_item.filename if use_last_item else None,
                None,
            )

            last_item = item
            counter.processed += 1
        else:
            logger.warning(
                "%s orbit direction lookup table extraction skipped", item.id
            )
            counter.skipped += 1

    od_tables.save()

    return counter


def update_orbit_direction_tables(product, logger=None):
    """ Update orbit direction tables from product and collection. """
    if not logger:
        logger = getLogger(__name__)

    collection = product.collection

    thresholds = get_orbit_direction_thresholds(*collection.spacecraft_tuple)

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(*collection.spacecraft_tuple, collection.grade),
        **thresholds, logger=logger
    )

    def _check_neighbour_product(product):
        if product.identifier not in od_tables:
            raise DataIntegrityError(
                f"{product.identifier} not found in orbit direction lookup "
                "table!"
            )

    processed = _update_orbit_direction_tables(
        od_tables, collection, extract_product_item(product),
        check_product=_check_neighbour_product,
        **thresholds
    )

    od_tables.save()

    return processed


def _update_orbit_direction_tables(od_tables, collection, product_item,
                                   min_product_gap, max_product_gap,
                                   check_product=None, **_):

    if product_item.id in od_tables:
        return False

    def _extract_and_check_data_file(product):
        if product is None:
            return None, None
        if check_product:
            check_product(product)
        return product.identifier, get_data_file(product)

    product_id_before, data_file_before = _extract_and_check_data_file(
        find_product_by_time_interval(
            collection,
            product_item.start - max_product_gap,
            product_item.start - min_product_gap,
        )
    )

    _, data_file_after = _extract_and_check_data_file(
        find_product_by_time_interval(
            collection,
            product_item.end + min_product_gap,
            product_item.end + max_product_gap,
        )
    )

    od_tables.update(
        product_item.id,
        product_item.filename,
        product_id_before,
        data_file_before,
        data_file_after,
    )

    return True


def get_orbit_direction_thresholds(mission, spacecraft):
    """ Get orbit direction thresholds for the given spacecraft identifier. """
    return OD_THRESHOLDS.get((mission, spacecraft), OD_THRESHOLDS_DEFAULT)


def get_orbit_direction_tables(mission, spacecraft, grade):
    """ Get orbit direction tables for the given spacecraft identifier. """
    try:
        return (
            cache_path(ORBIT_DIRECTION_GEO_FILE[(mission, spacecraft, grade)]),
            cache_path(ORBIT_DIRECTION_MAG_FILE[(mission, spacecraft, grade)]),
        )
    except KeyError:
        raise ValueError(
            f"Unexpected mission/spacecraft/grade ids "
            f"{mission}/{spacecraft}/{grade or '<none>'}!"
        ) from None


def find_product_by_time_interval(collection, begin_time, end_time):
    """ Locate product matched by the given time interval. """
    return _find_product(
        collection.products,
        begin_time__lte=naive_to_utc(end_time),
        end_time__gte=naive_to_utc(begin_time)
    )


def find_product_by_id(identifier):
    """ Locate product matched by the given product identifier. """
    return _find_product(
        Product.objects, identifier=identifier,
        collection__in=ProductCollection.objects.filter(
            metadata__calculateOrbitDirection=True
        )
    )


def _find_product(query_set, **filters):
    products = list(
        query_set.prefetch_related('collection__type').filter(**filters)[:1]
    )
    return products[0] if products else None


ProductItem = namedtuple("ProductItem", ["id", "filename", "start", "end"])


def extract_product_item(product):
    """ Convert product model in into ProductItem named tuple. """
    return ProductItem(
        product.identifier,
        get_data_file(product),
        product.begin_time,
        product.end_time,
    )


def iter_product_items(collection):
    """ Yield ProductItem named tuples for products in the given collection. """

    products = iter(collection.products.order_by("begin_time"))

    try:
        product = next(products)
    except StopIteration:
        return

    for next_product in products:
        yield extract_product_item(product)
        product = next_product

    yield extract_product_item(product)


def get_data_file(product):
    """ Get product data file. """
    return product.get_location(product.collection.type.default_dataset_id)


def get_collection(collection_id):
    """ Get collection for the given collection identifier.
    Return None if no collection matched.
    """
    try:
        return ProductCollection.objects.select_related('spacecraft').get(
            identifier=collection_id
        )
    except ProductCollection.DoesNotExist:
        return None


class Counter():

    def __init__(self):
        self.total = 0
        self.processed = 0
        self.skipped = 0
        self.removed = 0
