#-------------------------------------------------------------------------------
#
# Update orbit tables for given MAGx_LR product.
#
# Authors: Martin Paces martin.paces@eox.at
#
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
#pylint: disable=missing-docstring

import re
from logging import getLogger
from optparse import make_option
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from eoxserver.backends.access import connect
from eoxserver.resources.coverages.management.commands import CommandOutputMixIn
from vires.cdf_util import cdf_open
from vires.models import ProductCollection
from vires.management.commands import cache_session
from vires.orbit_direction_update import OrbitDirectionTables


TIMEDELTA_MAX = timedelta(seconds=1.5)
TIMEDELTA_MIN = timedelta(seconds=0.5)
RE_MAG_LR_PRODUCT = re.compile("^(SW_OPER_MAG([A-Z])_LR_1B)_.*_MDR_MAG_LR(\.cdf)?$")
RE_MAG_LR_COLLECTION = re.compile("^(SW_OPER_MAG([A-Z])_LR_1B)$")


class Command(CommandOutputMixIn, BaseCommand):
    option_list = BaseCommand.option_list
    option_list = BaseCommand.option_list + (
        make_option(
            "-r", "--rebuild-collection",
            dest="collection_id", default=None, help=(
                "Force re-processing of a whole MAGx_LR collection. "
            )
        ),
    )
    args = "[<product> [<product> ...]]"

    help = """
        Update orbit direction tables from one or more MAGx_LR products.
    """

    @cache_session
    def handle(self, *args, **kwargs):
        print_command = lambda msg: self.print_msg(msg, 1)
        collection_id = kwargs.get('collection_id')
        counter = Counter()

        if collection_id:
            self.rebuild_collection(counter, collection_id)

        self.update_from_files(counter, *args, **kwargs)

        counter.print_report(print_command)

    def update_from_files(self, counter, *args, **kwargs):
        """ update orbit direction table from a list of products. """
        for data_file in args:
            try:
                product_id, processed = update_orbit_direction_tables(data_file)
            except Exception as error:
                self.print_traceback(error, kwargs)
                self.print_err(
                    "Processing of '%s' failed! Reason: %s" % (data_file, error)
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

    def rebuild_collection(self, counter, collection_id):
        """ Re-build orbit direction lookup tables for the given collection. """

        match = RE_MAG_LR_COLLECTION.match(collection_id)
        if not match:
            raise CommandError("%s is not a MAGx_LR collection!" % collection_id)
        collection_id, spacecraft = match.groups()

        try:
            od_geo_file = settings.VIRES_ORBIT_DIRECTION_GEO_FILE[spacecraft]
            od_mag_file = settings.VIRES_ORBIT_DIRECTION_MAG_FILE[spacecraft]
        except KeyError:
            raise ValueError("Invalid spacecraft identifier %s!" % spacecraft)

        od_tables = OrbitDirectionTables(
            od_geo_file, od_mag_file, reset=True, logger=getLogger(__name__)
        )

        collection = get_collection(collection_id)
        if collection is None:
            self.print_wrn("Collection %s does not exist!" % collection_id)
            od_tables.save()
            return

        self.print_msg((
            "Rebuilding orbit direction lookup tables tables for collection "
            "%s ..." % collection_id
        ), 1)

        last_data_file = None
        last_end_time = None

        for data_file in list_collection(collection):
            counter.increment()
            product_id, start_time, end_time = get_product_id_and_time_range(data_file)
            if not last_data_file or last_end_time < start_time:
                data_file_before = last_data_file if (
                    last_data_file
                    and (start_time - last_end_time) < TIMEDELTA_MAX
                ) else None
                od_tables.update(data_file, data_file_before, None)
                last_data_file = data_file
                last_end_time = end_time
                counter.increment_processed()
                self.print_msg(
                    "%s orbit direction lookup table extracted" % product_id
                )
            else:
                self.print_wrn(
                    "%s orbit direction lookup table extraction skipped"
                    "" % product_id
                )
                counter.increment_skipped()

        od_tables.save()


def update_orbit_direction_tables(data_file):
    product_id, start_time, end_time = get_product_id_and_time_range(data_file)

    match = RE_MAG_LR_PRODUCT.match(product_id)
    if not match:
        raise ValueError("%s is not a MAGx_LR product!" % product_id)
    collection_id, spacecraft, _ = match.groups()

    try:
        od_geo_file = settings.VIRES_ORBIT_DIRECTION_GEO_FILE[spacecraft]
        od_mag_file = settings.VIRES_ORBIT_DIRECTION_MAG_FILE[spacecraft]
    except KeyError:
        raise ValueError("Invalid spacecraft identifier %s!" % spacecraft)

    od_tables = OrbitDirectionTables(
        od_geo_file, od_mag_file, logger=getLogger(__name__)
    )

    if product_id in od_tables:
        return product_id, False

    collection = get_collection(collection_id)
    if collection is None:
        raise ValueError("Collection %s does not exist!" % collection_id)

    data_file_before = find_product_data_file(
        collection, start_time - TIMEDELTA_MAX, start_time - TIMEDELTA_MIN
    )
    data_file_after = find_product_data_file(
        collection, end_time + TIMEDELTA_MIN, end_time + TIMEDELTA_MAX
    )

    od_tables.update(data_file, data_file_before, data_file_after)
    od_tables.save()

    return product_id, True


def find_product_data_file(collection, begin_time, end_time):
    """ Locate product matched by the given time interval. """
    products = [
        item.cast() for item in collection.eo_objects.filter(
            begin_time__lte=end_time, end_time__gte=begin_time
        )[:1] if item.iscoverage
    ]
    if not products:
        return None
    return connect(products[0].data_items.all()[0])


def list_collection(collection):
    """ Locate product matched by the given time interval. """
    return (
        connect(item.cast().data_items.all()[0]) for item
        in collection.eo_objects.order_by("begin_time") if item.iscoverage
    )


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

    def increment(self, count=1):
        self._total += count

    def increment_processed(self, count=1):
        self._processed += count

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

        if self._total == 0:
            print_fcn("No file processed.")
