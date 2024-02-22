#-------------------------------------------------------------------------------
#
# Testing CDF file handling
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring, invalid-name, too-many-arguments

import unittest
from os import remove
from os.path import exists
from datetime import datetime, timedelta
from numpy import arange, vectorize, array
from spacepy import pycdf
from vires.time_util import (
    datetime_to_mjd2000, datetime_to_unix_epoch
)
from vires.cdf_util import (
    CDF_EPOCH_TYPE, cdf_open,
    cdf_rawtime_to_datetime, cdf_rawtime_to_unix_epoch,
    cdf_rawtime_to_mjd2000, datetime_to_cdf_rawtime,
    mjd2000_to_cdf_rawtime,
    cdf_rawtime_to_datetime64, datetime64_to_cdf_rawtime,
)
from vires.tests import ArrayMixIn


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

    def test_datetime_to_cdf_rawtime_scalar(self):
        with cdf_open(self.FILE) as cdf:
            self.assertAllEqual(array([
                datetime_to_cdf_rawtime(dt, CDF_EPOCH_TYPE)
                for dt in cdf['time']
            ]), cdf.raw_var('time')[:])

    def test_cdf_rawtime_to_datetime_scalar(self):
        with cdf_open(self.FILE) as cdf:
            self.assertAllEqual(array([
                cdf_rawtime_to_datetime(rt, CDF_EPOCH_TYPE)
                for rt in cdf.raw_var('time')[:]
            ]), cdf['time'][:])

    def test_datetime_to_cdf_rawtime(self):
        with cdf_open(self.FILE) as cdf:
            self.assertAllEqual(
                datetime_to_cdf_rawtime(cdf['time'][:], CDF_EPOCH_TYPE),
                cdf.raw_var('time')[:]
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

    def test_mjd2000_to_cdf_rawtime(self):
        with cdf_open(self.FILE) as cdf:
            time_cdf_epoch = cdf.raw_var('time')[:]
            time_mjd2000 = cdf_rawtime_to_mjd2000(
                time_cdf_epoch, CDF_EPOCH_TYPE
            )
            self.assertAllEqual(
                mjd2000_to_cdf_rawtime(time_mjd2000, CDF_EPOCH_TYPE),
                time_cdf_epoch
            )

    def test_cdf_rawtime_to_unix_epoch(self):
        v_datetime_to_unix_epoch = vectorize(datetime_to_unix_epoch)
        with cdf_open(self.FILE) as cdf:
            self.assertAllAlmostEqual(
                cdf_rawtime_to_unix_epoch(
                    cdf.raw_var('time')[:], CDF_EPOCH_TYPE
                ), v_datetime_to_unix_epoch(cdf['time'][:]), 1e-5
            )


class TestCDFEpochTimeBase01(TestCDFEpochTime00):
    FILE = "./test_tmp_cdf_epoch1.cdf"
    START = datetime(2016, 3, 30, 0, 0, 0)
    STOP = datetime(2016, 3, 31, 0, 0, 0)
    STEP = timedelta(seconds=7)

if __name__ == "__main__":
    unittest.main()
