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
from numpy import asarray, datetime64, timedelta64
from eoxmagmod import mjd2000_to_decimal_year, eval_qdlatlon
from ..cdf_util import cdf_open
from ..cdf_write_util import CdfTypeEpoch
from .table import OrbitDirectionTable
from .common import NOMINAL_SAMPLING
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

    def __init__(self, geo_table_filename, mag_table_filename, reset=False,
                 logger=None):
        self.logger = logger or getLogger(__name__)
        self._geo_table = GeoOrbitDirectionTable(
            geo_table_filename, reset, logger=self.logger
        )
        self._mag_table = QDOrbitDirectionTable(
            mag_table_filename, reset, logger=self.logger
        )

    def __contains__(self, product_id):
        return (
            product_id in self._geo_table #and product_id in self._mag_table
        )

    @property
    def changed(self):
        """ Return true if the tables changed and should be saved. """
        return self._geo_table.changed #or self._mag_table.changed

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
        body = load_data_from_product(data_file)
        start_time, end_time = body.times[[0, -1]]
        margin_before = timedelta64(0, 'ms')
        margin_after = NOMINAL_SAMPLING

        data_items = []

        if data_file_before is not None:
            head = load_data_from_product(
                data_file_before, slice(-INPUT_MARGIN, None)
            )
            margin_before = start_time - head.times[-TRIM_MARGIN:][0]
            data_items.append(head)
            del head

        data_items.append(body)
        del body

        if data_file_after is not None:
            tail = load_data_from_product(
                data_file_after, slice(None, INPUT_MARGIN)
            )
            margin_after = max(
                NOMINAL_SAMPLING, tail.times[:TRIM_MARGIN][-1] - end_time
            )
            data_items.append(tail)
            del tail

        data = InputData.join(*data_items)
        del data_items

        self._geo_table.update(
            extract_orbit_directions(*get_times_and_latitudes(*data)),
            product_id, start_time, end_time, margin_before, margin_after,
        )

        self._mag_table.update(
            extract_orbit_directions(*get_times_and_qd_latitudes(*data)),
            product_id, start_time, end_time, margin_before, margin_after,
        )

        self.logger.info(
            "%s orbit direction lookup tables extracted", product_id
        )


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


def load_data_from_product(filename, slice_=Ellipsis):
    """ Load data concatenated from a single product. """
    with cdf_open(filename) as cdf:
        times = CdfTypeEpoch.decode(cdf.raw_var("Timestamp")[slice_])
        lats = cdf["Latitude"][slice_]
        lons = cdf["Longitude"][slice_]
        rads = cdf["Radius"][slice_]
    return InputData(times, lats, lons, rads)
