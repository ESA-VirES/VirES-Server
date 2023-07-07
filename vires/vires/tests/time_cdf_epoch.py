#-------------------------------------------------------------------------------
#
# CDF_EPOCH time conversion utilities - tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,no-self-use,line-too-long

from unittest import TestCase, main
from datetime import datetime
from numpy import array, nan
from numpy.testing import assert_equal
from vires.time_cdf_epoch import (
    cdf_epoch_to_utc_datetime,
    cdf_epoch_to_utc_datetime64_us,
    cdf_epoch_to_utc_datetime64_ms,
    cdf_epoch_to_unix_epoch,
    cdf_epoch_to_mjd2000,
    utc_datetime_to_cdf_epoch,
    utc_datetime64_us_to_cdf_epoch,
    utc_datetime64_ms_to_cdf_epoch,
    mjd2000_to_cdf_epoch,
    DT_EPOCH_2000,
    DT_EPOCH_1970,
    DT_MIN,
    DT_MAX,
    DT_INVALID_VALUE,
    CDF_EPOCH_INVALID_VALUE,
    CDF_EPOCH_PADDING_VALUE,
    CDF_EPOCH_1970,
    CDF_EPOCH_2000,
    CDF_EPOCH_DT_LOWER_BOUND,
    CDF_EPOCH_DT_UPPER_BOUND,
)


class TestCDFEpochTimeConversions(TestCase):

    def test_utc_datetime_to_cdf_epoch(self):
        self.assertEqual(CDF_EPOCH_INVALID_VALUE, utc_datetime_to_cdf_epoch(DT_INVALID_VALUE))
        self.assertEqual(CDF_EPOCH_DT_LOWER_BOUND, utc_datetime_to_cdf_epoch(DT_MIN))
        self.assertEqual(CDF_EPOCH_INVALID_VALUE, utc_datetime_to_cdf_epoch(DT_MAX))
        self.assertEqual(CDF_EPOCH_1970, utc_datetime_to_cdf_epoch(DT_EPOCH_1970))
        self.assertEqual(CDF_EPOCH_2000, utc_datetime_to_cdf_epoch(DT_EPOCH_2000))
        # CDF_EPOCH is not precise enough to keep exact microseconds
        self.assertEqual(63839882268123.000, utc_datetime_to_cdf_epoch(datetime(2023, 1, 2, 12, 37, 48, 123000)))
        self.assertEqual(63839882268123.456, utc_datetime_to_cdf_epoch(datetime(2023, 1, 2, 12, 37, 48, 123456)))

    def test_cdf_epoch_to_utc_datetime(self):
        self.assertEqual(DT_INVALID_VALUE, cdf_epoch_to_utc_datetime(CDF_EPOCH_INVALID_VALUE))
        self.assertEqual(DT_INVALID_VALUE, cdf_epoch_to_utc_datetime(CDF_EPOCH_PADDING_VALUE))
        self.assertEqual(DT_MIN, cdf_epoch_to_utc_datetime(CDF_EPOCH_DT_LOWER_BOUND))
        self.assertEqual(DT_INVALID_VALUE, cdf_epoch_to_utc_datetime(CDF_EPOCH_DT_UPPER_BOUND))

        self.assertEqual(DT_EPOCH_1970, cdf_epoch_to_utc_datetime(CDF_EPOCH_1970))
        self.assertEqual(DT_EPOCH_2000, cdf_epoch_to_utc_datetime(CDF_EPOCH_2000))
        # CDF_EPOCH is not precise enough to keep exact microseconds
        self.assertEqual(datetime(2023, 1, 2, 12, 37, 48, 123000), cdf_epoch_to_utc_datetime(63839882268123.000))
        self.assertEqual(datetime(2023, 1, 2, 12, 37, 48, 123453), cdf_epoch_to_utc_datetime(63839882268123.456))

    def test_cdf_epoch_to_utc_datetime64_us(self):
        source = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
            63839882268123.456,
        ])
        expected = array([
            "NaT",
            "0000-01-01",
            "1970-01-01",
            "2000-01-01",
            "2023-01-02T12:37:48.123000",
            "2023-01-02T12:37:48.123453",
        ], "datetime64[us]")
        assert_equal(expected, cdf_epoch_to_utc_datetime64_us(source))

    def test_utc_datetime64_us_to_cdf_epoch(self):
        source = array([
            "NaT",
            "0000-01-01",
            "1970-01-01",
            "2000-01-01",
            "2023-01-02T12:37:48.123000",
            "2023-01-02T12:37:48.123453",
        ], "datetime64[us]")
        expected = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
            63839882268123.456,
        ])
        assert_equal(expected, utc_datetime64_us_to_cdf_epoch(source))

    def test_cdf_epoch_to_utc_datetime64_ms(self):
        source = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
            63839882268123.456,
        ])
        expected = array([
            "NaT",
            "0000-01-01",
            "1970-01-01",
            "2000-01-01",
            "2023-01-02T12:37:48.123",
            "2023-01-02T12:37:48.123",
        ], "datetime64[ms]")
        assert_equal(expected, cdf_epoch_to_utc_datetime64_ms(source))

    def test_utc_datetime64_ms_to_cdf_epoch(self):
        source = array([
            "NaT",
            "0000-01-01",
            "1970-01-01",
            "2000-01-01",
            "2023-01-02T12:37:48.123",
        ], "datetime64[ms]")
        expected = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
        ])
        assert_equal(expected, utc_datetime64_ms_to_cdf_epoch(source))

    def test_cdf_epoch_to_unix_epoch(self):
        source = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
            63839882268123.456,
        ])
        expected = array([
            nan,
            nan,
            0.0,
            (DT_EPOCH_2000 - DT_EPOCH_1970).total_seconds(),
            1672663068.123000145,
            1672663068.123453140,
        ])
        assert_equal(expected, cdf_epoch_to_unix_epoch(source))

    def test_cdf_epoch_to_mjd2000(self):
        source = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
            63839882268123.456,
        ])
        expected = array([
            nan,
            nan,
            -(DT_EPOCH_2000 - DT_EPOCH_1970).days,
            0.0,
            8402.526251423611029,
            8402.526251428855176,
        ])
        assert_equal(expected, cdf_epoch_to_mjd2000(source))

    def test_mjd2000_to_cdf_rawtime(self):
        source = array([
            nan,
            -(DT_EPOCH_2000 - DT_EPOCH_1970).days,
            0.0,
            8402.526251423611029,
            8402.526251428855176,
        ])
        expected = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_1970,
            CDF_EPOCH_2000,
            63839882268123.000,
            63839882268123.456,
        ])
        assert_equal(expected, mjd2000_to_cdf_epoch(source))


if __name__ == "__main__":
    main()
