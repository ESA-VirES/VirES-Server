#-------------------------------------------------------------------------------
#
# CDF_TT2000 time conversion utilities - test
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
from numpy import array, nan, inf
from numpy.testing import assert_equal
from vires.time_cdf_tt2000 import (
    convert_tt2000_to_utc2000_ns,
    convert_utc2000_to_tt2000_ns,
    cdf_tt2000_to_cdf_epoch,
    cdf_epoch_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime,
    utc_datetime_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime64_ns,
    utc_datetime64_ns_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime64_us,
    utc_datetime64_us_to_cdf_tt2000,
    cdf_tt2000_to_unix_epoch,
    cdf_tt2000_to_mjd2000,
    mjd2000_to_cdf_tt2000,
    CDF_TT2000_INVALID_VALUE,
    CDF_TT2000_PADDING_VALUE,
    CDF_TT2000_MIN_VALID,
    CDF_TT2000_MAX_VALID,
    CDF_TT2000_DT64_US_LOWER_BOUND,
    CDF_TT2000_DT64_US_UPPER_BOUND,
    CDF_TT2000_DT64_NS_UPPER_BOUND,
    CDF_EPOCH_INVALID_VALUE,
    CDF_EPOCH_PADDING_VALUE,
    CDF_EPOCH_LOWER_BOUND,
    CDF_EPOCH_UPPER_BOUND,
    DT_INVALID_VALUE,
    DT64_NS_MIN_VALID,
    DT64_NS_MAX_VALID,
    DT64_NS_LOWER_BOUND,
    DT64_NS_UPPER_BOUND,
    DT64_US_LOWER_BOUND,
    DT64_US_UPPER_BOUND,
    MJD2000_LOWER_BOUND,
    MJD2000_UPPER_BOUND,
)


class TestCDFTT2000TimeConversions(TestCase):

    def test_convert_tt2000_to_utc2000_ns(self):
        source = array([-883655957816000000, -43135816000000, 0, 694267269184000000])
        expected = array([-883612800000000000, 0, 43135816000000, 694310400000000000])
        result, _ = convert_tt2000_to_utc2000_ns(source)
        assert_equal(expected, result)

    def test_convert_utc2000_to_tt2000_ns(self):
        source = array([-883612800000000000, 0, 43135816000000, 694310400000000000])
        expected = array([-883655957816000000, -43135816000000, 0, 694267269184000000])
        result, _ = convert_utc2000_to_tt2000_ns(source)
        assert_equal(expected, result)

    def test_cdf_tt2000_to_cdf_epoch(self):
        source = array([
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_PADDING_VALUE,
            -883655957816000000,
            0,
            725803269184000000,
            CDF_TT2000_MIN_VALID,
            CDF_TT2000_MAX_VALID,
        ])
        expected = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            62230291200000.0,
            63113947135816.0,
            63839750400000.0,
            CDF_EPOCH_LOWER_BOUND,
            72337319167670.78125000000,
        ])
        assert_equal(expected, cdf_tt2000_to_cdf_epoch(source))

    def test_cdf_epoch_to_cdf_tt2000(self):
        source = array([
            CDF_EPOCH_INVALID_VALUE,
            CDF_EPOCH_PADDING_VALUE,
            62230291200000.0,
            63113904000000.0,
            63839750400000.0,
            CDF_EPOCH_LOWER_BOUND, # min. CDF_EPOCH still converted to CDF_TT2000
            CDF_EPOCH_UPPER_BOUND, # max. CDF_EPOCH still converted to CDF_TT2000
        ])
        expected = array([
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_PADDING_VALUE,
            -883655957816000000,
            -43135816000000,
            725803269184000000,
            -9223372036854773438,
            9223372036854765625
        ])
        assert_equal(expected, cdf_epoch_to_cdf_tt2000(source))

    def test_cdf_tt2000_to_utc_datetime(self):
        self.assertEqual(datetime(1972, 1, 1), cdf_tt2000_to_utc_datetime(-883655957816000000))
        self.assertEqual(datetime(2000, 1, 1, 11, 58, 55, 816000), cdf_tt2000_to_utc_datetime(0))
        self.assertEqual(datetime(2023, 1, 1), cdf_tt2000_to_utc_datetime(725803269184000000))
        self.assertEqual(DT_INVALID_VALUE, cdf_tt2000_to_utc_datetime(CDF_TT2000_INVALID_VALUE))
        self.assertEqual(DT_INVALID_VALUE, cdf_tt2000_to_utc_datetime(CDF_TT2000_PADDING_VALUE))
        self.assertEqual(datetime(1707, 9, 22, 12, 12, 10, 961224), cdf_tt2000_to_utc_datetime(CDF_TT2000_MIN_VALID))
        self.assertEqual(datetime(2292, 4, 11, 11, 46, 7, 670775), cdf_tt2000_to_utc_datetime(CDF_TT2000_MAX_VALID))

    def test_utc_datetime_to_cdf_tt2000(self):
        self.assertEqual(-883655957816000000, utc_datetime_to_cdf_tt2000(datetime(1972, 1, 1)))
        self.assertEqual(-43135816000000, utc_datetime_to_cdf_tt2000(datetime(2000, 1, 1)))
        self.assertEqual(725803269184000000, utc_datetime_to_cdf_tt2000(datetime(2023, 1, 1)))
        self.assertEqual(CDF_TT2000_INVALID_VALUE, utc_datetime_to_cdf_tt2000(DT_INVALID_VALUE))
        self.assertEqual(CDF_TT2000_INVALID_VALUE, utc_datetime_to_cdf_tt2000(datetime(1707, 9, 22, 12, 12, 10, 961224)))
        self.assertEqual(-9223372036854775000, utc_datetime_to_cdf_tt2000(datetime(1707, 9, 22, 12, 12, 10, 961225))) # lower bound
        self.assertEqual(9223372036854775000, utc_datetime_to_cdf_tt2000(datetime(2292, 4, 11, 11, 46, 7, 670775))) # upper bound
        self.assertEqual(CDF_TT2000_INVALID_VALUE, utc_datetime_to_cdf_tt2000(datetime(2292, 4, 11, 11, 46, 7, 670776)))

    def test_cdf_tt2000_to_utc_datetime64_ns(self):
        source = array([
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_PADDING_VALUE,
            -883655957816000000,
            0,
            725803269184000000,
            CDF_TT2000_MIN_VALID,
            CDF_TT2000_DT64_NS_UPPER_BOUND,
            CDF_TT2000_DT64_NS_UPPER_BOUND,
            CDF_TT2000_MAX_VALID,
        ])
        expected = array([
            "NaT",
            "NaT",
            "1972-01-01",
            "2000-01-01T11:58:55.816",
            "2023-01-01",
            DT64_NS_LOWER_BOUND,
            DT64_NS_UPPER_BOUND,
            DT64_NS_MAX_VALID,
            "NaT",
        ], "datetime64[ns]")
        assert_equal(expected, cdf_tt2000_to_utc_datetime64_ns(source))

    def test_cdf_tt2000_to_utc_datetime64_us(self):
        source = array([
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_PADDING_VALUE,
            -883655957816000000,
            0,
            725803269184000000,
            CDF_TT2000_MIN_VALID,
            CDF_TT2000_DT64_US_LOWER_BOUND,
            CDF_TT2000_DT64_US_UPPER_BOUND,
            CDF_TT2000_MAX_VALID,
        ])
        expected = array([
            "NaT",
            "NaT",
            "1972-01-01",
            "2000-01-01T11:58:55.816",
            "2023-01-01",
            DT64_US_LOWER_BOUND - 1,
            DT64_US_LOWER_BOUND,
            DT64_US_UPPER_BOUND,
            DT64_US_UPPER_BOUND,
        ], "datetime64[us]")
        assert_equal(expected, cdf_tt2000_to_utc_datetime64_us(source))

    def test_utc_datetime64_ns_to_cdf_tt2000(self):
        source = array([
            "NaT",
            "1972-01-01",
            "2000-01-01",
            "2000-01-01T11:58:55.816",
            "2023-01-01",
            DT64_NS_MIN_VALID,
            DT64_NS_LOWER_BOUND,
            DT64_NS_UPPER_BOUND,
            DT64_NS_MAX_VALID,
        ], "datetime64[ns]")
        expected = array([
            CDF_TT2000_INVALID_VALUE,
            -883655957816000000,
            -43135816000000,
            0,
            725803269184000000,
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_MIN_VALID,
            CDF_TT2000_DT64_NS_UPPER_BOUND,
            CDF_TT2000_DT64_NS_UPPER_BOUND,
        ])
        assert_equal(expected, utc_datetime64_ns_to_cdf_tt2000(source))

    def test_utc_datetime64_us_to_cdf_tt2000(self):
        source = array([
            "NaT",
            "1972-01-01",
            "2000-01-01",
            "2000-01-01T11:58:55.816",
            "2023-01-01",
            DT64_US_LOWER_BOUND - 1,
            DT64_US_LOWER_BOUND,
            DT64_US_UPPER_BOUND,
            DT64_US_UPPER_BOUND + 1,
        ], "datetime64[us]")
        expected = array([
            CDF_TT2000_INVALID_VALUE,
            -883655957816000000,
            -43135816000000,
            0,
            725803269184000000,
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_DT64_US_LOWER_BOUND,
            CDF_TT2000_DT64_US_UPPER_BOUND,
            CDF_TT2000_INVALID_VALUE,
        ])
        assert_equal(expected, utc_datetime64_us_to_cdf_tt2000(source))

    def test_cdf_tt2000_to_unix_epoch(self):
        source = array([
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_PADDING_VALUE,
            -883655957816000000,
            0,
            725803269184000000,
            CDF_TT2000_MIN_VALID,
            CDF_TT2000_MAX_VALID,
        ], "int64")
        expected = array([
            nan,
            nan,
            63072000.0,
            946727935.816,
            1672531200.0,
            -8276644069.038775444030761719,
            10170099967.6707763671875000,
        ], "float64")
        assert_equal(expected, cdf_tt2000_to_unix_epoch(source))

    def test_cdf_tt2000_to_mjd2000(self):
        source = array([
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_PADDING_VALUE,
            -883655957816000000,
            -43135816000000,
            0,
            725803269184000000,
            CDF_TT2000_MIN_VALID,
            CDF_TT2000_MAX_VALID,
        ], "int64")
        expected = array([
            nan,
            nan,
            -10227.0,
            0.0,
            0.499257129629629703426730,
            8401.0,
            -106751.491539800641476176679134,
            106752.490366559912217780947685,
        ], "float64")
        assert_equal(expected, cdf_tt2000_to_mjd2000(source))

    def test_mjd2000_to_cdf_tt2000(self):
        source = array([
            nan,
            -10227.0,
            0.0,
            0.499257129629629703426730,
            8401.0,
            MJD2000_LOWER_BOUND,
            MJD2000_UPPER_BOUND,
            -inf,
            inf,

        ], "float64")
        expected = array([
            CDF_TT2000_INVALID_VALUE,
            -883655957816000000,
            -43135816000000,
            0,
            725803269184000000,
            -9223372036854775424,
            9223372036854775158,
            CDF_TT2000_INVALID_VALUE,
            CDF_TT2000_INVALID_VALUE,
        ], "int64")
        assert_equal(expected, mjd2000_to_cdf_tt2000(source))


if __name__ == "__main__":
    main()
