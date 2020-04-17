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
from datetime import timedelta
from vires.cdf_util import cdf_open
from vires.time_util import naive_to_utc
from vires.models import ProductCollection, Product
from vires.orbit_direction_update import (
    OrbitDirectionTables, DataIntegrityError,
)
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    ORBIT_DIRECTION_GEO_FILE, ORBIT_DIRECTION_MAG_FILE,
)

TIMEDELTA_MAX = timedelta(seconds=1.5)
TIMEDELTA_MIN = timedelta(seconds=0.5)




def sync_orbit_direction_tables(collection, logger=None, counter=None):
    """ Sync orbit direction lookup tables for the given collection. """

    if not logger:
        logger = getLogger(__name__)

    if not counter:
        counter = Counter()

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(collection.metadata.get('spacecraft', '-')),
        logger=logger
    )

    logger.info(
        "Synchronizing orbit direction lookup tables for collection "
        "%s ...", collection.identifier
    )

    for product_id in od_tables.products.difference(
            product.identifier for product in list_collection(collection)
        ):
        od_tables.remove(product_id)
        counter.removed += 1

    for product in list_collection(collection):
        counter.total += 1
        processed = _update_orbit_direction_tables(
            od_tables, collection, product
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

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(collection.metadata.get('spacecraft', '-')),
        reset=True, logger=logger
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

    last_data_file = None
    last_end_time = None

    for product in list_collection(collection):
        counter.total += 1

        data_file = get_data_file(product)
        _, start_time, end_time = get_product_id_and_time_range(data_file)

        if not last_data_file or last_end_time < start_time:
            data_file_before = last_data_file if (
                last_data_file
                and (start_time - last_end_time) < TIMEDELTA_MAX
            ) else None
            od_tables.update(
                product.identifier, data_file, data_file_before, None
            )
            last_data_file = data_file
            last_end_time = end_time
            counter.processed += 1
        else:
            logger.warning(
                "%s orbit direction lookup table extraction skipped",
                product.identifier
            )
            counter.skipped += 1

    od_tables.save()

    return counter


def update_orbit_direction_tables(product):
    """ Update orbit direction tables from product and collection. """
    collection = product.collection

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(collection.metadata.get('spacecraft', '-')),
        logger=getLogger(__name__)
    )

    def _check_neighbour_product(product):
        if product.identifier not in od_tables:
            raise DataIntegrityError(
                "%s not found in orbit direction lookup tables! " % (
                    product.identifier,
                )
            )

    processed = _update_orbit_direction_tables(
        od_tables, collection, product, _check_neighbour_product
    )

    od_tables.save()

    return processed


def _update_orbit_direction_tables(od_tables, collection, product,
                                   check_product=None):

    if product.identifier in od_tables:
        return False

    data_file = get_data_file(product)
    _, start_time, end_time = get_product_id_and_time_range(data_file)

    def _extract_and_check_data_file(product):
        if product is None:
            return None
        if check_product:
            check_product(product)
        return get_data_file(product)

    data_file_before = _extract_and_check_data_file(
        find_product_by_time_interval(
            collection, start_time - TIMEDELTA_MAX, start_time - TIMEDELTA_MIN
        )
    )
    data_file_after = _extract_and_check_data_file(
        find_product_by_time_interval(
            collection, end_time + TIMEDELTA_MIN, end_time + TIMEDELTA_MAX
        )
    )

    od_tables.update(
        product.identifier, data_file, data_file_before, data_file_after
    )

    return True


def get_orbit_direction_tables(spacecraft):
    """ Get orbit direction tables for the given spacecraft identifier. """
    try:
        return (
            cache_path(ORBIT_DIRECTION_GEO_FILE[spacecraft]),
            cache_path(ORBIT_DIRECTION_MAG_FILE[spacecraft]),
        )
    except KeyError:
        raise ValueError("Invalid spacecraft identifier %s!" % spacecraft)


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


def list_collection(collection):
    """ Locate product matched by the given time interval. """
    return collection.products.order_by("begin_time")


def get_data_file(product):
    """ Get product data file. """
    return product.get_location()


def get_collection(collection_id):
    """ Get collection for the given collection identifier.
    Return None if no collection matched.
    """
    try:
        return ProductCollection.objects.get(
            identifier=collection_id
        )
    except ProductCollection.DoesNotExist:
        return None


def get_product_id_and_time_range(data_file):
    with cdf_open(data_file) as cdf:
        return str(cdf.attrs['TITLE']), cdf['Timestamp'][0], cdf['Timestamp'][-1]


class Counter():

    def __init__(self):
        self.total = 0
        self.processed = 0
        self.skipped = 0
        self.removed = 0
