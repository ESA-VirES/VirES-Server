#-------------------------------------------------------------------------------
#
# Orbit direction - lookup tables update
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=too-many-arguments, too-few-public-methods

from logging import getLogger
from os.path import basename
from numpy import (
    asarray, datetime64, timedelta64,
    concatenate, argsort, arange,
)
from eoxmagmod import mjd2000_to_decimal_year, eval_qdlatlon
from ..cdf_util import cdf_open
from ..cdf_data_reader import read_cdf_data
from .table import OrbitDirectionTable
from .util import InputData
from .extract import extract_orbit_directions

MS2DAYS = 1.0/(24*60*60*1e3) # milliseconds to days scale factor
INPUT_MARGIN = 6 # number of samples needed from the surrounding products
TRIM_MARGIN = 4 # number of samples needed to smoothly merge surrounding products


class GeoOrbitDirectionTable(OrbitDirectionTable):
    """ Geographic orbit direction lookup table class. """
    DESCRIPTION = "Orbit directions boundaries in geographic coordinates."


class QDOrbitDirectionTable(OrbitDirectionTable):
    """ Quasi-dipole orbit direction lookup table class """
    DESCRIPTION = "Orbit directions boundaries in quasi-dipole coordinates."


class OrbitDirectionTables():
    """ Single spacecraft orbit direction lookup tables class. """

    def __init__(self, geo_table_filename, mag_table_filename,
                 nominal_sampling, gap_threshold,
                 reset=False, logger=None, **_):

        self.nominal_sampling = timedelta_to_timedelta64ms(nominal_sampling)
        self.gap_threshold = timedelta_to_timedelta64ms(gap_threshold)

        print(f"nominal_sampling = {self.nominal_sampling}")
        print(f"gap_threshold = {self.gap_threshold}")

        self.logger = logger or getLogger(__name__)
        self._geo_table = GeoOrbitDirectionTable(
            geo_table_filename, reset, logger=self.logger
        )
        self._mag_table = QDOrbitDirectionTable(
            mag_table_filename, reset, logger=self.logger
        )

    def __contains__(self, product_id):
        return (
            product_id in self._geo_table and product_id in self._mag_table
        )

    @property
    def changed(self):
        """ Return true if the tables changed and should be saved. """
        return self._geo_table.changed or self._mag_table.changed

    @property
    def products(self):
        """ Iterate products of the lookup table. """
        product_set = set()
        product_set.update(self._geo_table.products)
        product_set.update(self._mag_table.products)
        return product_set

    def save(self):
        """ Save the tables. """
        self._geo_table.save()
        self._mag_table.save()

    def remove(self, product_id):
        """ Remove product from the lookup tables. """
        self._geo_table.remove(product_id)
        self._mag_table.remove(product_id)
        self.logger.info(
            "%s removed from orbit direction lookup tables", product_id
        )

    def update(self, product_id, data_file, data_file_before, data_file_after):
        """ Update orbit direction tables. """
        data, start_time, end_time, margin_before, margin_after = (
            self._load_data(data_file, data_file_before, data_file_after)
        )

        self._geo_table.update(
            extract_orbit_directions(
                *get_times_and_latitudes(*data),
                nominal_sampling=self.nominal_sampling,
                gap_threshold=self.gap_threshold,
            ),
            product_id, start_time, end_time, margin_before, margin_after,
        )

        self._mag_table.update(
            extract_orbit_directions(
                *get_times_and_qd_latitudes(*data),
                nominal_sampling=self.nominal_sampling,
                gap_threshold=self.gap_threshold,
            ),
            product_id, start_time, end_time, margin_before, margin_after,
        )

        self.logger.info(
            "%s orbit direction lookup tables extracted", product_id
        )

    def _load_data(self, data_file, data_file_before, data_file_after):
        body = self._load_data_from_product(data_file)
        start_time, end_time = body.times[[0, -1]]
        margin_before = timedelta64(0, 'ms')
        margin_after = self.nominal_sampling

        data_items = []

        if data_file_before is not None:
            head = self._load_data_from_product(
                data_file_before, slice(-INPUT_MARGIN, None)
            )
            margin_before = start_time - head.times[-TRIM_MARGIN:][0]
            data_items.append(head)

        data_items.append(body)

        if data_file_after is not None:
            tail = self._load_data_from_product(
                data_file_after, slice(None, INPUT_MARGIN)
            )
            margin_after = max(
                margin_after, tail.times[:TRIM_MARGIN][-1] - end_time
            )
            data_items.append(tail)

        return (
            InputData.join(*data_items),
            start_time, end_time,
            margin_before, margin_after,
        )

    def _load_data_from_product(self, filename, slice_=Ellipsis):
        """ Load data concatenated from a single product. """
        def _load(filename):
            with cdf_open(filename) as cdf:
                dataset = read_cdf_data(
                    cdf, ["Timestamp", "Latitude", "Longitude", "Radius"]
                )
            return InputData(
                dataset["Timestamp"],
                dataset["Latitude"],
                dataset["Longitude"],
                dataset["Radius"],
            )

        def _sanitize(data):
            times = data.times

            if times.size < 2:
                return data

            index_sort = argsort(times)
            if (index_sort != arange(times.size)).any():
                self.logger.warning(
                    "%s: Timestamp values are not sorted!", basename(filename)
                )

            index_unique = concatenate(([0], 1 + (
                times[index_sort[1:]] > times[index_sort[:-1]]
            ).nonzero()[0]))

            if index_unique.size < index_sort.size:
                self.logger.warning(
                    "%s: Timestamp values are not unique!", basename(filename)
                )

            return data[index_sort[index_unique]]

        return _sanitize(_load(filename))[slice_]


def get_times_and_latitudes(times, lats, lons, rads): # pylint: disable=unused-argument
    """ Get geographic latitudes for the given input parameters. """
    return times, lats


def get_times_and_qd_latitudes(times, lats, lons, rads):
    """ Get quasi-dipole latitudes for the given input parameters. """
    qd_lats, _ = eval_qdlatlon(
        lats, lons, rads*1e-3,
        mjd2000_to_decimal_year(datetime64_to_mjd2000(times))
    )
    return times, qd_lats


def datetime64_to_mjd2000(times):
    """ Convert datetime64 array to MJD2000. """
    return MS2DAYS*(
        asarray(times, 'M8[ms]') - datetime64('2000-01-01', 'ms')
    ).astype('float64')


def timedelta_to_timedelta64ms(td_obj):
    """ Convert datetime.timedelta to numpy.timedelta64('ms'). """
    return timedelta64(int(td_obj.total_seconds() * 1e3), "ms")
