#-------------------------------------------------------------------------------
#
# Update orbit tables from MAGx_LR products.
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

import re
from logging import getLogger
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from eoxserver.backends.access import connect
from eoxserver.resources.coverages.management.commands import CommandOutputMixIn
from vires.cdf_util import cdf_open
from vires.models import ProductCollection, Product
from vires.management.commands import cache_session
from vires.orbit_direction_update import (
    OrbitDirectionTables, DataIntegrityError,
)


TIMEDELTA_MAX = timedelta(seconds=1.5)
TIMEDELTA_MIN = timedelta(seconds=0.5)
RE_MAG_LR_PRODUCT = re.compile(r"^(SW_OPER_MAG([A-Z])_LR_1B)_.*_MDR_MAG_LR$")
RE_MAG_LR_COLLECTION = re.compile(r"^(SW_OPER_MAG([A-Z])_LR_1B)$")


class Command(CommandOutputMixIn, BaseCommand):

    help = """ Update orbit direction lookup tables. """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("product_id", nargs="*")
        parser.add_argument(
            "-c", "--collection", dest="collection_id", required=True,
            help="Mandatory collection identifier."
        )
        parser.add_argument(
            "-r", "--rebuild", dest="rebuild_collection",
            action="store_true", default=False, help=(
                "Force re-processing of the whole collection. "
            )
        )
        parser.add_argument(
            "-u", "--update", dest="update_collection",
            action="store_true", default=False, help=(
                "Update lookup tables for the given collection."
            )
        )

    @cache_session
    def handle(self, *args, **kwargs):
        print_command = lambda msg: self.print_msg(msg, 1)

        collection_id = kwargs['collection_id']
        collection = get_collection(collection_id)
        if collection is None:
            raise ValueError("Collection %s does not exist!" % collection_id)

        counter = Counter()
        if kwargs.get('rebuild_collection', False):
            self.rebuild_collection(counter, collection)
        if kwargs.get('update_collection', False):
            self.update_collection(counter, collection)
        else:
            self.update_from_products(
                counter, collection, kwargs['product_id'], **kwargs
            )

        counter.print_report(print_command)

    def update_from_products(self, counter, collection, product_ids, **kwargs):
        """ update orbit direction table from a list of products. """

        def _update_from_product(product_id):
            product = find_product_by_id(product_id)
            if product is None:
                raise ValueError("%s not found!" % product_id)
            return update_orbit_direction_tables(collection, product)

        for product_id in product_ids:
            try:
                processed = _update_from_product(product_id)
            except DataIntegrityError as error:
                self.print_wrn(str(error))
                self.update_collection(counter, collection)
            except Exception as error:
                self.print_traceback(error, kwargs)
                self.print_err(
                    "Processing of %s failed! Reason: %s" % (product_id, error)
                )
                counter.increment_failed()
            else:
                if processed:
                    counter.increment_processed()
                    self.print_msg(
                        "%s orbit direction lookup table extracted" % product_id
                    )
                else:
                    counter.increment_skipped()
                    self.print_msg(
                        "%s orbit direction lookup table extraction skipped"
                        "" % product_id
                    )
            finally:
                counter.increment()

    def update_collection(self, counter, collection):
        """ Synchronize orbit direction lookup tables for the given collection.
        """
        sync_orbit_direction_tables(collection, logger=self, counter=counter)

    def rebuild_collection(self, counter, collection):
        """ Re-build orbit direction lookup tables for the given collection.
        """
        rebuild_orbit_direction_tables(collection, logger=self, counter=counter)

    def info(self, format_, *args):
        self.print_msg(format_ % args)

    def warn(self, format_, *args):
        self.print_msg(format_ % args)

    def error(self, format_, *args):
        self.print_msg(format_ % args)


def sync_orbit_direction_tables(collection, logger=None, counter=None):
    """ Sync orbit direction lookup tables for the given collection. """

    if not logger:
        logger = getLogger(__name__)

    if not counter:
        counter = Counter()

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(
            collection_to_spacecraft(collection.identifier)
        ), logger=logger
    )

    logger.info(
        "Synchronizing orbit direction lookup tables for collection "
        "%s ...", collection.identifier
    )

    for product_id in od_tables.products.difference(
            product.identifier for product in list_collection(collection)
        ):
        od_tables.remove(product_id)
        counter.increment_removed()

    for product in list_collection(collection):
        counter.increment()
        processed = _update_orbit_direction_tables(
            od_tables, collection, product
        )

        if processed:
            counter.increment_processed()
        else:
            counter.increment_skipped()

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
        *get_orbit_direction_tables(
            collection_to_spacecraft(collection.identifier)
        ), reset=True, logger=logger
    )

    collection = get_collection(collection.identifier)
    if collection is None:
        logger.warn(
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
        counter.increment()

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
            counter.increment_processed()
        else:
            logger.warn(
                "%s orbit direction lookup table extraction skipped",
                product.identifier
            )
            counter.increment_skipped()

    od_tables.save()

    return counter


def update_orbit_direction_tables(collection, product):
    """ Update orbit direction tables from product and collection. """
    if collection.range_type != product.range_type:
        raise ValueError(
            "The product range type does not match the collection range type!"
        )

    od_tables = OrbitDirectionTables(
        *get_orbit_direction_tables(
            collection_to_spacecraft(collection.identifier)
        ), logger=getLogger(__name__)
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
            settings.VIRES_ORBIT_DIRECTION_GEO_FILE[spacecraft],
            settings.VIRES_ORBIT_DIRECTION_MAG_FILE[spacecraft],
        )
    except KeyError:
        raise ValueError("Invalid spacecraft identifier %s!" % spacecraft)


def collection_to_spacecraft(collection_id):
    try:
        return settings.VIRES_COL2SAT[collection_id]
    except KeyError:
        raise ValueError(
            "Cannot determine spacecraft for collection %s" % collection_id
        )


def find_product_by_time_interval(collection, begin_time, end_time):
    """ Locate product matched by the given time interval. """
    return _find_product(
        collection.eo_objects, begin_time__lte=end_time, end_time__gte=begin_time
    )


def find_product_by_id(product_id):
    """ Locate product matched by the given time interval. """
    return _find_product(Product.objects, identifier=product_id)


def _find_product(query_set, **filters):
    products = [
        item.cast() for item in query_set.filter(**filters)[:1]
        if item.iscoverage
    ]
    return products[0] if products else None


def list_collection(collection):
    """ Locate product matched by the given time interval. """
    return (
        item.cast() for item in collection.eo_objects.order_by("begin_time")
        if item.iscoverage
    )


def get_data_file(product):
    """ Get product data file. """
    return connect(product.data_items.all()[0])


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


class Counter(object):

    def __init__(self):
        self._total = 0
        self._processed = 0
        self._failed = 0
        self._skipped = 0
        self._removed = 0

    def increment(self, count=1):
        self._total += count

    def increment_processed(self, count=1):
        self._processed += count

    def increment_removed(self, count=1):
        self._removed += count

    def increment_failed(self, count=1):
        self._failed += count

    def increment_skipped(self, count=1):
        self._skipped += count

    def print_report(self, print_fcn):
        if self._processed > 0:
            print_fcn(
                "%d of %d product(s) processed."
                % (self._processed, self._total)
            )

        if self._skipped > 0:
            print_fcn(
                "%d of %d product(s) skipped."
                % (self._skipped, self._total)
            )

        if self._failed > 0:
            print_fcn(
                "Failed to process %d of %d product(s)."
                % (self._failed, self._total)
            )

        if self._removed > 0:
            print_fcn(
                "%d old product(s) removed from lookup tables." % self._removed
            )

        if self._total == 0:
            print_fcn("No file processed.")
