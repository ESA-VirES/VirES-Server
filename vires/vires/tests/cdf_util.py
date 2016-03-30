#-------------------------------------------------------------------------------
#
# Testing Auxiliary Data Handling
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=missing-docstring, invalid-name

import unittest
from os import remove
from os.path import exists
from StringIO import StringIO
from datetime import datetime, timedelta
from numpy import arange, linspace, vectorize, isnan, logical_not
from scipy.interpolate import interp1d
from spacepy import pycdf

from vires.time_util import (
    datetime_to_mjd2000, datetime_to_unix_epoch, datetime_to_decimal_year,
)
from vires.cdf_util import (
    CDF_EPOCH_TYPE, cdf_open, cdf_time_subset, cdf_time_interp,
    cdf_rawtime_to_datetime, cdf_rawtime_to_unix_epoch,
    cdf_rawtime_to_mjd2000, cdf_rawtime_to_decimal_year,
    cdf_rawtime_to_decimal_year_fast,
)
from vires.aux import parse_dst
from vires.tests.aux import TEST_DST, DATA_DST, ArrayMixIn

class TestCDFEpochTime00(ArrayMixIn, unittest.TestCase):
    FILE = "./test_tmp_cdf_epoch2.cdf"
    START = datetime(1980, 1, 1, 0, 0, 0)
    STOP = datetime(2100, 1, 1, 0, 0, 0)
    STEP = timedelta(days=368, seconds=123, microseconds=13000)

    def get_time(self):
        start = pycdf.lib.datetime_to_epoch(self.START)
        stop = pycdf.lib.datetime_to_epoch(self.STOP)
        step = self.STEP.total_seconds() * 1e3
        return arange(start, stop, step)

    def setUp(self):
        if exists(self.FILE):
            remove(self.FILE)
        with cdf_open(self.FILE, "w") as cdf:
            cdf.new('time', self.get_time(), CDF_EPOCH_TYPE)

    def tearDown(self):
        if exists(self.FILE):
            remove(self.FILE)

    def test_sanity_check(self):
        time = self.get_time()
        with cdf_open(self.FILE) as cdf:
            self.assertAllEqual(
                self.get_time(), cdf.raw_var('time')[:]
            )
            self.assertAllEqual(
                self.START + self.STEP * arange(0, time.size),
                cdf['time'][:]
            )

    def test_cdf_rawtime_to_datetime(self):
        with cdf_open(self.FILE) as cdf:
            self.assertAllEqual(
                cdf_rawtime_to_datetime(cdf.raw_var('time')[:], CDF_EPOCH_TYPE),
                cdf['time'][:]
            )

    def test_cdf_rawtime_to_mjd2000(self):
        v_datetime_to_mjd2000 = vectorize(datetime_to_mjd2000)
        with cdf_open(self.FILE) as cdf:
            self.assertAllAlmostEqual(
                cdf_rawtime_to_mjd2000(cdf.raw_var('time')[:], CDF_EPOCH_TYPE),
                v_datetime_to_mjd2000(cdf['time'][:]), 1e-9
            )

    def test_cdf_rawtime_to_unix_epoch(self):
        v_datetime_to_unix_epoch = vectorize(datetime_to_unix_epoch)
        with cdf_open(self.FILE) as cdf:
            self.assertAllAlmostEqual(
                cdf_rawtime_to_unix_epoch(
                    cdf.raw_var('time')[:], CDF_EPOCH_TYPE
                ), v_datetime_to_unix_epoch(cdf['time'][:]), 1e-5
            )

    def test_cdf_rawtime_to_decimal_year(self):
        v_datetime_to_decimal_year = vectorize(datetime_to_decimal_year)
        with cdf_open(self.FILE) as cdf:
            self.assertAllAlmostEqual(
                cdf_rawtime_to_decimal_year(
                    cdf.raw_var('time')[:], CDF_EPOCH_TYPE
                ), v_datetime_to_decimal_year(cdf['time'][:]), 1e-5
            )


class TestCDFEpochTimeBase01(TestCDFEpochTime00):
    FILE = "./test_tmp_cdf_epoch1.cdf"
    START = datetime(2016, 3, 30, 0, 0, 0)
    STOP = datetime(2016, 3, 31, 0, 0, 0)
    STEP = timedelta(seconds=7)

    def test_cdf_rawtime_to_decimal_year_fast(self):
        v_datetime_to_decimal_year = vectorize(datetime_to_decimal_year)
        with cdf_open(self.FILE) as cdf:
            self.assertAllAlmostEqual(
                cdf_rawtime_to_decimal_year_fast(
                    cdf.raw_var('time')[:], CDF_EPOCH_TYPE, 2016
                ), v_datetime_to_decimal_year(cdf['time'][:]), 1e-5
            )


class TestCDF(ArrayMixIn, unittest.TestCase):
    FILE = "./test_tmp_cdf.cdf"

    def setUp(self):
        with cdf_open(self.FILE, "w") as cdf:
            cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
                parse_dst(StringIO(TEST_DST))
            )

    def tearDown(self):
        if exists(self.FILE):
            remove(self.FILE)

    def _cdf_time_subset(self, fields, start, stop, idx_start, idx_stop, margin=0):
        """ Testing CDF read. """
        with cdf_open(self.FILE) as cdf:
            for field, value in cdf_time_subset(cdf, start, stop, fields, margin):
                self.assertEqual(value.shape, (idx_stop - idx_start,))
                self.assertAllEqual(value, cdf[field][idx_start:idx_stop])
                self.assertAllEqual(value, DATA_DST[field][idx_start:idx_stop])

    def _cdf_time_interp(self, start, stop, count, **kwargs):
        time = linspace(start, stop, count)
        with cdf_open(self.FILE) as cdf:
            data = dict(cdf_time_interp(cdf, time, ("dst",), **kwargs))

        values = interp1d(
            DATA_DST['time'], DATA_DST['dst'], bounds_error=False, **kwargs
        )(time)

        self.assertEqual(data['dst'].shape, (count,))
        self.assertEqual(isnan(data['dst']).shape, isnan(values).shape)
        self.assertAllAlmostEqual(
            data['dst'][logical_not(isnan(values))],
            values[logical_not(isnan(values))], delta=1e-9
        )

    def test_cdf_time_subset_margin1(self):
        # full interval
        self._cdf_time_subset(('time', 'dst'), -729.97917, -728.56250, 0, 35, 1)
        self._cdf_time_subset(('time', 'dst'), -731.00, -728.00, 0, 35, 1)
        self._cdf_time_subset(('time', 'dst'), -729.97, -728.57, 0, 35, 1)
        # inner subset
        self._cdf_time_subset(('time', 'dst'), -729.60, -729.00, 9, 25, 1)
        # partial overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -729.00, 0, 25, 1)
        # partial overlap - upper
        self._cdf_time_subset(('time', 'dst'), -729.60, -725.00, 9, 35, 1)
        # no overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -730.00, 0, 0, 1)
        self._cdf_time_subset(('time', 'dst'), -733.00, -732.00, 0, 0, 1)
        # no overlap - upper
        self._cdf_time_subset(('time', 'dst'), -728.54, -725.00, 0, 0, 1)
        self._cdf_time_subset(('time', 'dst'), -724.00, -725.00, 0, 0, 1)

    def test_cdf_time_subset(self):
        # full interval
        self._cdf_time_subset(('time', 'dst'), -729.97917, -728.56250, 0, 35)
        self._cdf_time_subset(('time', 'dst'), -731.00, -728.00, 0, 35)
        # inner subset
        self._cdf_time_subset(('time', 'dst'), -729.60, -729.00, 10, 24)
        # partial overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -729.00, 0, 24)
        # partial overlap - upper
        self._cdf_time_subset(('time', 'dst'), -729.60, -725.00, 10, 35)
        # no overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -730.00, 0, 0)
        self._cdf_time_subset(('time', 'dst'), -733.00, -732.00, 0, 0)
        # no overlap - upper
        self._cdf_time_subset(('time', 'dst'), -728.54, -725.00, 0, 0)
        self._cdf_time_subset(('time', 'dst'), -724.00, -725.00, 0, 0)

    def test_cdf_time_interp(self):
        # full overlap
        self._cdf_time_interp(-732.00, -728.00, 80)
        self._cdf_time_interp(-732.00, -728.00, 80, kind="nearest")
        # touching the bounds
        self._cdf_time_interp(-728.56251, -728.00, 5)
        self._cdf_time_interp(-728.56251, -728.00, 5, kind="nearest")
        self._cdf_time_interp(-732.00, -729.979169, 5)
        self._cdf_time_interp(-732.00, -729.979169, 5, kind="nearest")
        # out of bounds
        self._cdf_time_interp(-728.00, -726.00, 5)
        self._cdf_time_interp(-728.00, -726.00, 5, kind="nearest")
        self._cdf_time_interp(-734.00, -732.00, 5)
        self._cdf_time_interp(-734.00, -732.00, 5, kind="nearest")
        # single value
        self._cdf_time_interp(-729.00, -729.00, 1)
        self._cdf_time_interp(-729.00, -729.00, 1, kind="nearest")


if __name__ == "__main__":
    unittest.main()
