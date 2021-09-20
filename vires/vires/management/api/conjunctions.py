#-------------------------------------------------------------------------------
#
# Orbit conjunction management API
#
# Authors: Martin Paces martin.paces@eox.at
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
#pylint: disable=missing-docstring

from logging import getLogger
from datetime import timedelta
from vires.dataset import Dataset
from vires.cdf_util import cdf_open
from vires.cdf_data_reader import read_cdf_time_series, sorted_range_slice
from vires.time_util import naive_to_utc, datetime_to_datetime64
from vires.models import ProductCollection, Product
from vires.cache_util import cache_path
from vires.data.vires_settings import ORBIT_CONJUNCTION_FILE
from vires.conjunctions import ConjunctionsTable

TIMEDELTA_BUFFER = timedelta(seconds=15.5)
TIMEDELTA_MARGIN = timedelta(seconds=1.5)


class Counter():
    def __init__(self):
        self.total = 0
        self.processed = 0
        self.skipped = 0
        self.removed = 0


def sync_conjunctions_table(collection1, collection2, logger=None, counter=None):
    """ Sync conjunction table for the given spacecraft collections. """
    logger, counter = _init_logger_and_counter(logger, counter)

    logger.info(
        "%s conjunctions table synchronization ...",
        get_spacecrafts_string(collection1, collection2),
    )

    table = ConjunctionsTable(
        tuple(sorted((
            collection1.formatted_spacecraft,
            collection2.formatted_spacecraft
        ))),
        cache_path(
            ORBIT_CONJUNCTION_FILE[
                get_spacecrafts_tuple(collection1, collection2)
            ]
        ),
        #logger=logger,
    )

    product_pairs = pair_products(
        iter_products(collection1),
        iter_products(collection2),
    )

    for _, _, product1, product2 in product_pairs:
        counter.total += 2
        processed = _update_conjunctions_table(
            table, product1, product2, logger, skip_existing=True
        )
        if processed:
            counter.processed += 2
        else:
            counter.skipped += 2

    table.save()


def rebuild_conjunctions_table(collection1, collection2, logger=None, counter=None):
    """ Re-build conjunction table for the given spacecraft collections. """
    logger, counter = _init_logger_and_counter(logger, counter)

    logger.info(
        "%s conjunctions table rebuild ...",
        get_spacecrafts_string(collection1, collection2),
    )

    table = ConjunctionsTable(
        tuple(sorted((
            collection1.formatted_spacecraft,
            collection2.formatted_spacecraft
        ))),
        cache_path(
            ORBIT_CONJUNCTION_FILE[
                get_spacecrafts_tuple(collection1, collection2)
            ]
        ),
        reset=True,
        #logger=logger,
    )

    product_pairs = pair_products(
        iter_products(collection1),
        iter_products(collection2),
    )

    for _, _, product1, product2 in product_pairs:
        counter.total += 2
        _update_conjunctions_table(table, product1, product2, logger)
        counter.processed += 2

    table.save()


def update_conjunctions_tables(product, logger=None, counter=None):
    """ Update all applicable conjunction tables from the given product. """
    logger, counter = _init_logger_and_counter(logger, counter)

    collection = product.collection
    other_collections = find_pair_collections(collection)

    for other_collection in other_collections:
        update_conjunctions_table(
            product, other_collection, logger=logger, counter=counter
        )


def update_conjunctions_table(product, other_collection, logger=None, counter=None):
    """ Update conjunction table from the given product. """
    logger, counter = _init_logger_and_counter(logger, counter)

    collection = product.collection

    counter.total += 1
    other_products = find_products_by_time_interval(
        other_collection, product.begin_time, product.end_time
    )

    if not other_products:
        logger.info(
            "%s conjunctions table update from %s skipped",
            get_spacecrafts_string(product.collection, other_collection),
            product.identifier,
        )
        counter.skipped += 1
        return

    table = ConjunctionsTable(
        tuple(sorted((
            collection.formatted_spacecraft,
            other_collection.formatted_spacecraft
        ))),
        cache_path(
            ORBIT_CONJUNCTION_FILE[
                get_spacecrafts_tuple(collection, other_collection)
            ]
        ),
        #logger=logger,
    )

    for other_product in other_products:
        _update_conjunctions_table(table, product, other_product, logger)
        counter.total += 1
        counter.processed += 1

    counter.processed += 1

    table.save()


def _update_conjunctions_table(table, product, other_product, logger,
                               skip_existing=False):
    """ Update conjunction table from the given product. """
    begin_time = max(product.begin_time, other_product.begin_time)
    end_time = min(product.end_time, other_product.end_time)

    product_pair = tuple(sorted([product.identifier, other_product.identifier]))

    if skip_existing and product_pair in table:
        return False # skip already processed product

    table.update(
        datetime_to_datetime64(begin_time - TIMEDELTA_MARGIN),
        datetime_to_datetime64(end_time + TIMEDELTA_MARGIN),
        orbit1=_load_orbits(
            product.collection,
            begin_time + TIMEDELTA_BUFFER,
            end_time - TIMEDELTA_BUFFER,
        ),
        orbit2=_load_orbits(
            other_product.collection,
            begin_time + TIMEDELTA_BUFFER,
            end_time - TIMEDELTA_BUFFER,
        ),
        product_pair=(
            datetime_to_datetime64(begin_time),
            datetime_to_datetime64(end_time),
            tuple(sorted([product.identifier, other_product.identifier]))
        )
    )

    return True


def _load_orbits(collection, begin_time, end_time):

    time_slice = sorted_range_slice(
        datetime_to_datetime64(begin_time),
        datetime_to_datetime64(end_time),
    )

    products = find_products_by_time_interval(collection, begin_time, end_time)

    dataset = Dataset()

    for product in products:
        with cdf_open(get_data_file(product)) as cdf:
            dataset.append(
                read_cdf_time_series(
                    cdf, time_slice=time_slice,
                    variables=["Timestamp", "Latitude", "Longitude"],
                    time_variable="Timestamp",
                )
            )

    return dataset


def pair_products(products1, products2):
    """ Pair time-overlapping products. """

    class _Range():
        def __init__(self, product):
            self.start = product.begin_time
            self.end = product.end_time
            self.product = product

        def trim_start(self, time):
            self.start = time

        @property
        def is_empty(self):
            return self.start >= self.end

    def _iter_ranges(products):
        for product in products:
            yield _Range(product)

    def _next(iterator):
        for item in iterator:
            return item
        return None

    ranges1 = _iter_ranges(products1)
    ranges2 = _iter_ranges(products2)

    range1 = _next(ranges1)
    range2 = _next(ranges2)

    while range1 and range2:
        if range1.start < range2.start:
            range1.trim_start(range2.start)
        elif range2.start < range1.start:
            range2.trim_start(range1.start)
        else: # range1.start == range1.start
            end = min(range1.end, range2.end)
            yield range1.start, end, range1.product, range2.product
            range1.trim_start(end)
            range2.trim_start(end)

        if range1.is_empty:
            range1 = _next(ranges1)
        if range2.is_empty:
            range2 = _next(ranges2)


def find_pair_collections(collection):
    """ Find pair orbit collection matching given collection. """
    spacecraft = collection.spacecraft
    other_spacecrafts = {
        sc1 if spacecraft == sc2 else sc2
        for sc1, sc2 in ORBIT_CONJUNCTION_FILE
        if spacecraft in (sc1, sc2)
    }
    query = ProductCollection.objects.order_by('identifier')
    query = query.filter(metadata__calculateConjunctions=True)

    return [
        collection for collection in query
        if collection.spacecraft in other_spacecrafts
    ]


def find_products_by_time_interval(collection, begin_time, end_time):
    """ Locate product matched by the given time interval. """
    return _find_products(
        collection.products,
        begin_time__lte=naive_to_utc(end_time),
        end_time__gte=naive_to_utc(begin_time)
    )


def iter_products(collection):
    """ Iterate products from a collection. """

    return _find_products(collection.products)


def find_product_by_id(identifier):
    """ Find product matched by the given product identifier. """
    return _find_product(
        Product.objects, identifier=identifier,
        collection__in=ProductCollection.objects.filter(
            metadata__calculateOrbitDirection=True
        )
    )


def _find_product(query_set, **filters):
    products = list(_find_products(query_set, **filters)[:1])
    return products[0] if products else None


def _find_products(query_set, **filters):
    return (
        query_set
        .order_by('begin_time')
        .prefetch_related('collection__type')
        .filter(**filters)
    )

def get_data_file(product):
    """ Get product data file. """
    return product.get_location(product.collection.type.default_dataset_id)


def get_spacecrafts_string(collection, other_collection):
    return "%s/%s" % tuple(sorted((
        collection.formatted_spacecraft,
        other_collection.formatted_spacecraft
    )))


def get_spacecrafts_tuple(collection, other_collection):
    return tuple(sorted((collection.spacecraft, other_collection.spacecraft)))


def _init_logger_and_counter(logger, counter):
    """ Decorator initializing default parameters. """
    return logger or getLogger(__name__), counter or Counter()
