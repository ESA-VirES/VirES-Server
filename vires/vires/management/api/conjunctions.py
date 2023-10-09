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
from collections import namedtuple
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
TIMEDELTA_SAMPLING = timedelta(seconds=1)


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
            collection1.spacecraft_string,
            collection2.spacecraft_string
        ))),
        cache_path(
            ORBIT_CONJUNCTION_FILE[
                get_spacecrafts_tuple(collection1, collection2)
            ]
        ),
        #logger=logger,
    )

    product_items_pairs = pair_products(
        iter_product_items(collection1),
        iter_product_items(collection2),
    )

    for _, _, item1, item2 in product_items_pairs:
        counter.total += 2
        processed = _update_conjunctions_table(
            table, item1, item2, logger, skip_existing=True
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
            collection1.spacecraft_string,
            collection2.spacecraft_string
        ))),
        cache_path(
            ORBIT_CONJUNCTION_FILE[
                get_spacecrafts_tuple(collection1, collection2)
            ]
        ),
        reset=True,
        #logger=logger,
    )

    product_items_pairs = pair_products(
        iter_product_items(collection1),
        iter_product_items(collection2),
    )

    for _, _, item1, item2 in product_items_pairs:
        counter.total += 2
        _update_conjunctions_table(table, item1, item2, logger)
        counter.processed += 2

    table.save()


def update_conjunctions_tables(product, logger=None, counter=None):
    """ Update all applicable conjunction tables from the given product. """
    logger, counter = _init_logger_and_counter(logger, counter)

    for collection in find_pair_collections(product.collection):
        update_conjunctions_table(
            product, collection, logger=logger, counter=counter
        )


def update_conjunctions_table(product, other_collection, logger=None, counter=None):
    """ Update conjunction table from the given product. """
    logger, counter = _init_logger_and_counter(logger, counter)

    collection = product.collection

    # find trimming products
    def _find_next_product(product):
        for next_product in _find_products(
            product.collection.products,
            begin_time__gt=naive_to_utc(product.begin_time),
            begin_time__lte=naive_to_utc(product.end_time),
        ):
            return next_product
        return None

    product_item = extract_product_item(product, _find_next_product(product))

    counter.total += 1

    other_product_items = list(iter_product_items(
        other_collection,
        begin_time__lte=naive_to_utc(product_item.trim),
        end_time__gte=naive_to_utc(product_item.start),
    ))

    if not other_product_items:
        logger.info(
            "%s conjunctions table update from %s skipped",
            get_spacecrafts_string(product.collection, other_collection),
            product.identifier,
        )
        counter.skipped += 1
        return

    table = ConjunctionsTable(
        tuple(sorted((
            collection.spacecraft_string,
            other_collection.spacecraft_string
        ))),
        cache_path(
            ORBIT_CONJUNCTION_FILE[
                get_spacecrafts_tuple(collection, other_collection)
            ]
        ),
        #logger=logger,
    )

    counter.processed += 1

    for other_product_item in other_product_items:
        _update_conjunctions_table(table, product_item, other_product_item, logger)
        counter.total += 1
        counter.processed += 1

    table.save()


def _update_conjunctions_table(table, product_item, other_product_item, logger,
                               skip_existing=False):
    """ Update conjunction table from the given product. """
    begin_time = max(product_item.start, other_product_item.start)
    end_time = min(product_item.trim, other_product_item.trim)

    product_pair = tuple(sorted([product_item.id, other_product_item.id]))

    if skip_existing and product_pair in table:
        return False # skip already processed product

    table.update(
        datetime_to_datetime64(begin_time - TIMEDELTA_MARGIN),
        datetime_to_datetime64(end_time + TIMEDELTA_MARGIN),
        orbit1=_load_orbit_data(
            product_item.collection,
            begin_time + TIMEDELTA_BUFFER,
            end_time - TIMEDELTA_BUFFER,
        ),
        orbit2=_load_orbit_data(
            other_product_item.collection,
            begin_time + TIMEDELTA_BUFFER,
            end_time - TIMEDELTA_BUFFER,
        ),
        product_pair=(
            datetime_to_datetime64(begin_time),
            datetime_to_datetime64(end_time),
            tuple(sorted([product_item.id, other_product_item.id]))
        ),
        previous_pair_trim_time=datetime_to_datetime64(
            begin_time - TIMEDELTA_SAMPLING # fixme: get real time
        ),
    )

    return True


def _load_orbit_data(collection, begin_time, end_time):

    product_items = iter_product_items(
        collection,
        begin_time__lte=naive_to_utc(end_time),
        end_time__gte=naive_to_utc(begin_time),
    )

    dataset = Dataset()

    for item in product_items:
        time_slice = sorted_range_slice(
            datetime_to_datetime64(max(begin_time, item.start)),
            datetime_to_datetime64(min(end_time, item.trim)),
        )
        with cdf_open(item.filename) as cdf:
            dataset.append(
                read_cdf_time_series(
                    cdf, time_slice=time_slice,
                    variables=["Timestamp", "Latitude", "Longitude"],
                    time_variable="Timestamp",
                )
            )

    return dataset


def pair_products(product_items1, product_items2):
    """ Pair time-overlapping products. """

    class _Range():
        def __init__(self, product_item):
            self.start = product_item.start
            self.end = (
                product_item.trim if product_item.trim else product_item.end
            )
            self.item = product_item

        def trim_start(self, time):
            self.start = time

        @property
        def is_empty(self):
            return self.start >= self.end

    def _iter_ranges(product_items):
        for item in product_items:
            yield _Range(item)

    def _next(iterator):
        for item in iterator:
            return item
        return None

    ranges1 = _iter_ranges(product_items1)
    ranges2 = _iter_ranges(product_items2)

    range1 = _next(ranges1)
    range2 = _next(ranges2)

    while range1 and range2:
        if range1.start < range2.start:
            range1.trim_start(range2.start)
        elif range2.start < range1.start:
            range2.trim_start(range1.start)
        else: # range1.start == range1.start
            end = min(range1.end, range2.end)
            yield range1.start, end, range1.item, range2.item
            range1.trim_start(end)
            range2.trim_start(end)

        if range1.is_empty:
            range1 = _next(ranges1)
        if range2.is_empty:
            range2 = _next(ranges2)


def find_pair_collections(collection):
    """ Find pair orbit collection matching given collection. """

    def _extract_selection_key(collection):
        return (*collection.spacecraft_tuple, collection.grade)

    key = _extract_selection_key(collection)
    other_keys = {
        key1 if key == key2 else key2
        for key1, key2 in ORBIT_CONJUNCTION_FILE
        if key in (key1, key2)
    }
    query = ProductCollection.objects.select_related('spacecraft').order_by('identifier')
    query = query.filter(metadata__calculateConjunctions=True)

    return [
        collection for collection in query
        if _extract_selection_key(collection) in other_keys
    ]


ProductItem = namedtuple("ProductItem", [
    "id", "filename", "collection", "start", "end", "trim",
])


def extract_product_item(product, next_product):
    """ Convert product model in into ProductItem named tuple. """
    return ProductItem(
        product.identifier,
        get_data_file(product),
        product.collection,
        product.begin_time,
        product.end_time,
        (
            next_product.begin_time - TIMEDELTA_SAMPLING # fixme: get real time
            if next_product and next_product.begin_time <= product.end_time
            else product.end_time
        )
    )


def iter_product_items(collection, **filters):
    """ Yield ProductItem named tuples for products in the given collection. """

    products = iter(_find_products(collection.products, **filters))

    try:
        product = next(products)
    except StopIteration:
        return

    for next_product in products:
        yield extract_product_item(product, next_product)
        product = next_product

    yield extract_product_item(product, None)


def find_products_by_id(identifier):
    """ Yield product matched by the given product identifier. """
    return _find_products(
        Product.objects, identifier=identifier,
        collection__in=ProductCollection.objects.filter(
            metadata__calculateOrbitDirection=True
        )
    )


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


def get_spacecrafts_string(collection1, collection2):

    def _format_collection(collection):
        if collection.grade:
            return f"{collection.spacecraft_string}[{collection.grade}]"
        return collection.spacecraft_string

    return "%s/%s" % tuple(sorted((
        _format_collection(collection1), _format_collection(collection2)
    )))


def get_spacecrafts_tuple(collection1, collection2):

    def _get_key(collection):
        return (*collection.spacecraft_tuple, collection.grade)

    return tuple(sorted(
        (_get_key(collection1), _get_key(collection2)),
        key=lambda v: (*v[:2], v[2] or ''),
    ))


def _init_logger_and_counter(logger, counter):
    """ Decorator initializing default parameters. """
    return logger or getLogger(__name__), counter or Counter()
