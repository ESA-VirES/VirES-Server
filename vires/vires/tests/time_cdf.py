#-------------------------------------------------------------------------------
#
# CDF time conversion utilities - tests
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
from datetime import datetime, timedelta
from numpy import asarray, stack, vectorize, int64, datetime64
from numpy.random import uniform, randint, random
from numpy.testing import assert_equal
from vires.time_cdf import (
    UnsupportedCDFTimeTypeError,
    CDF_EPOCH_TYPE,
    CDF_EPOCH16_TYPE,
    CDF_TIME_TT2000_TYPE,
    cdf_epoch16_to_cdf_epoch,
    convert_cdf_raw_times,
    cdf_rawtime_to_datetime64,
    datetime64_to_cdf_rawtime,
    cdf_rawtime_delta_in_seconds,
    cdf_rawtime_subtract_delta_in_seconds,
    cdf_rawtime_to_timedelta,
    timedelta_to_cdf_rawtime,
    datetime_to_cdf_rawtime,
    cdf_rawtime_to_datetime,
    cdf_rawtime_to_unix_epoch,
    cdf_rawtime_to_mjd2000,
    mjd2000_to_cdf_rawtime,
)
from vires.time_cdf_epoch import (
    milliseconds_to_timedelta,
    timedelta_to_milliseconds,
    utc_datetime_to_cdf_epoch,
    cdf_epoch_to_utc_datetime,
    utc_datetime64_us_to_cdf_epoch,
    cdf_epoch_to_utc_datetime64_us,
    mjd2000_to_cdf_epoch,
    cdf_epoch_to_mjd2000,
    cdf_epoch_to_unix_epoch,
)
from vires.time_cdf_tt2000 import (
    nanoseconds_to_timedelta,
    timedelta_to_nanoseconds,
    cdf_epoch_to_cdf_tt2000,
    cdf_tt2000_to_cdf_epoch,
    utc_datetime_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime,
    utc_datetime64_ns_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime64_ns,
    mjd2000_to_cdf_tt2000,
    cdf_tt2000_to_mjd2000,
    cdf_tt2000_to_unix_epoch,
)

# -----------------------------------------------------------------------------

class BaseCDFTimeConversionTest(TestCase):
    start = datetime(1970, 1, 1)
    end = datetime(2030, 1, 1)

    @classmethod
    def _get_random_epoch(cls, size=None):
        return uniform(
            utc_datetime_to_cdf_epoch(cls.start),
            utc_datetime_to_cdf_epoch(cls.end),
            size=size
        )

    @classmethod
    def _get_random_epoch16(cls, size=None):
        return stack((
            uniform(
                utc_datetime_to_cdf_epoch(cls.start) // 1000,
                utc_datetime_to_cdf_epoch(cls.end) // 1000,
                size=size,
            ),
            uniform(0.0, 1e12, size=size)
        ), axis=-1)

    @classmethod
    def _get_random_tt2000(cls, size=None):
        return randint(
            utc_datetime_to_cdf_tt2000(cls.start),
            utc_datetime_to_cdf_tt2000(cls.end),
            size=size, dtype="int64",
        )

    def _test(self, expected, tested_func, *args, **kwargs):
        result = tested_func(*args, **kwargs)
        assert_equal(expected, result)

# -----------------------------------------------------------------------------

class TestCDFTimeSubtraction(BaseCDFTimeConversionTest):
    """ Conversions of differences of CDF times to timedelta object. """

    @classmethod
    def _get_random_seconds(cls, size=None):
        return random(size=size) * (cls.end - cls.start).total_seconds() * 0.5

    def _test_cdf_rawtime_delta_in_seconds(self, expected, *args):
        self._test(expected, cdf_rawtime_delta_in_seconds, *args)

    def _test_cdf_rawtime_subtract_delta_in_seconds(self, expected, *args):
        self._test(expected, cdf_rawtime_subtract_delta_in_seconds, *args)

    def test_cdf_rawtime_delta_in_seconds_epoch(self):
        source1 = self._get_random_epoch(10)
        source2 = self._get_random_epoch(10)
        expected = (source1 - source2) * 1e-3
        self._test_cdf_rawtime_delta_in_seconds(
            expected, source1, source2, CDF_EPOCH_TYPE
        )

    def test_cdf_rawtime_delta_in_seconds_epoch16(self):
        source1 = self._get_random_epoch16(10)
        source2 = self._get_random_epoch16(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_delta_in_seconds(
                None, source1, source2, CDF_EPOCH16_TYPE
            )

    def test_cdf_rawtime_delta_in_seconds_tt2000(self):
        source1 = self._get_random_tt2000(10)
        source2 = self._get_random_tt2000(10)
        expected = (source1 - source2) * 1e-9
        self._test_cdf_rawtime_delta_in_seconds(
            expected, source1, source2, CDF_TIME_TT2000_TYPE
        )

    def test_cdf_rawtime_subtract_delta_in_seconds_epoch(self):
        source1 = self._get_random_epoch(10)
        source2 = self._get_random_seconds(10)
        expected = source1 - 1e3 * source2
        self._test_cdf_rawtime_subtract_delta_in_seconds(
            expected, source1, source2, CDF_EPOCH_TYPE
        )

    def test_cdf_rawtime_subtract_delta_in_seconds_epoch16(self):
        source1 = self._get_random_epoch16(10)
        source2 = self._get_random_seconds(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_subtract_delta_in_seconds(
                None, source1, source2, CDF_EPOCH16_TYPE
            )

    def test_cdf_rawtime_subtract_delta_in_seconds_tt2000(self):
        source1 = self._get_random_tt2000(10)
        source2 = self._get_random_seconds(10)
        expected = source1 - (source2 * 1000000000).astype("int64")
        self._test_cdf_rawtime_subtract_delta_in_seconds(
            expected, source1, source2, CDF_TIME_TT2000_TYPE
        )

# -----------------------------------------------------------------------------

class TestTimedeltaCDFTimeConversions(BaseCDFTimeConversionTest):
    """ Conversions of differences of CDF times to timedelta object. """
    @classmethod
    def _get_random_timedelta(cls):
        time_s = random() * (cls.end - cls.start).total_seconds()
        return timedelta(seconds=time_s)

    def _test_cdf_rawtime_to_timedelta(self, expected, *args):
        self._test(expected, cdf_rawtime_to_timedelta, *args)

    def _test_timedelta_to_cdf_rawtime(self, expected, *args):
        self._test(expected, timedelta_to_cdf_rawtime, *args)

    def test_cdf_rawtime_to_timedelta_epoch(self):
        source = float(self._get_random_epoch() - self._get_random_epoch())
        expected = milliseconds_to_timedelta(source)
        self._test_cdf_rawtime_to_timedelta(expected, source, CDF_EPOCH_TYPE)

    def test_cdf_rawtime_to_timedelta_epoch16(self):
        source = self._get_random_epoch16() - self._get_random_epoch16()
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_to_timedelta(None, source, CDF_EPOCH16_TYPE)

    def test_cdf_rawtime_to_timedelta_tt2000(self):
        source = int(self._get_random_tt2000() - self._get_random_tt2000())
        expected = nanoseconds_to_timedelta(source)
        self._test_cdf_rawtime_to_timedelta(expected, source, CDF_TIME_TT2000_TYPE)

    def test_timedelta_to_cdf_rawtime_epoch(self):
        source = self._get_random_timedelta()
        expected = timedelta_to_milliseconds(source)
        self._test_timedelta_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_timedelta_to_cdf_rawtime_epoch16(self):
        source = self._get_random_timedelta()
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_timedelta_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_timedelta_to_cdf_rawtime_tt2000(self):
        source = self._get_random_timedelta()
        expected = timedelta_to_nanoseconds(source)
        self._test_timedelta_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

# -----------------------------------------------------------------------------

class TestCDFTimeToCDFTimeConversions(BaseCDFTimeConversionTest):
    """ Conversions between different CDF time types.
    """

    def _test_convert_cdf_raw_times(self, expected, *args):
        self._test(expected, convert_cdf_raw_times, *args)

    def test_convert_cdf_raw_times_epoch_to_epoch(self):
        source = self._get_random_epoch(10)
        self._test_convert_cdf_raw_times(
            source, source, CDF_EPOCH_TYPE, CDF_EPOCH_TYPE
        )

    def test_convert_cdf_raw_times_epoch_to_epoch16(self):
        source = self._get_random_epoch(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_convert_cdf_raw_times(
                None, source, CDF_EPOCH_TYPE, CDF_EPOCH16_TYPE
            )

    def test_convert_cdf_raw_times_epoch_to_tt2000(self):
        source = self._get_random_epoch(10)
        expected = cdf_epoch_to_cdf_tt2000(source)
        self._test_convert_cdf_raw_times(
            expected, source, CDF_EPOCH_TYPE, CDF_TIME_TT2000_TYPE
        )

    def test_convert_cdf_raw_times_epoch16_to_epoch16(self):
        source = self._get_random_epoch16(10)
        self._test_convert_cdf_raw_times(
            source, source, CDF_EPOCH16_TYPE, CDF_EPOCH16_TYPE
        )

    def test_convert_cdf_raw_times_epoch16_to_epoch(self):
        source = self._get_random_epoch16(10)
        expected = cdf_epoch16_to_cdf_epoch(source)
        self._test_convert_cdf_raw_times(
            expected, source, CDF_EPOCH16_TYPE, CDF_EPOCH_TYPE
        )

    def test_convert_cdf_raw_times_epoch16_to_tt2000(self):
        source = self._get_random_epoch16(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_convert_cdf_raw_times(
                None, source, CDF_EPOCH16_TYPE, CDF_TIME_TT2000_TYPE
            )

    def test_convert_cdf_raw_times_tt2000_to_tt2000(self):
        source = self._get_random_tt2000(10)
        self._test_convert_cdf_raw_times(
            source, source, CDF_TIME_TT2000_TYPE, CDF_TIME_TT2000_TYPE
        )

    def test_convert_cdf_raw_times_tt2000_to_epoch(self):
        source = self._get_random_tt2000(10)
        expected = cdf_tt2000_to_cdf_epoch(source)
        self._test_convert_cdf_raw_times(
            expected, source, CDF_TIME_TT2000_TYPE, CDF_EPOCH_TYPE
        )

    def test_convert_cdf_raw_times_tt2000_to_epoch16(self):
        source = self._get_random_tt2000(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_convert_cdf_raw_times(
                None, source, CDF_TIME_TT2000_TYPE, CDF_EPOCH16_TYPE
            )

# -----------------------------------------------------------------------------

class TestDatetimeCDFTimeConversions(BaseCDFTimeConversionTest):
    """ Conversions between CDF times and datetime.datetime objects
    """

    @classmethod
    def _get_random_datetime(cls, size=None):

        def _get_datetime(factor):
            time_s = factor * (cls.end - cls.start).total_seconds()
            return cls.start + timedelta(seconds=time_s)

        if size is None:
            return _get_datetime(random())

        return vectorize(_get_datetime, otypes=('object',))(random(size=size))

    def _test_datetime_to_cdf_rawtime(self, expected, *args):
        self._test(expected, datetime_to_cdf_rawtime, *args)

    def _test_cdf_rawtime_to_datetime(self, expected, *args):
        self._test(expected, cdf_rawtime_to_datetime, *args)

    def test_datetime_to_cdf_rawtime_epoch_scalar(self):
        source = self._get_random_datetime()
        expected = utc_datetime_to_cdf_epoch(source)
        self._test_datetime_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_datetime_to_cdf_rawtime_epoch16_scalar(self):
        source = self._get_random_datetime()
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_datetime_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_datetime_to_cdf_rawtime_tt2000_scalar(self):
        source = self._get_random_datetime()
        expected = utc_datetime_to_cdf_tt2000(source)
        self._test_datetime_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_cdf_rawtime_to_datetime_epoch_scalar(self):
        source = self._get_random_epoch()
        expected = cdf_epoch_to_utc_datetime(source)
        self._test_cdf_rawtime_to_datetime(expected, source, CDF_EPOCH_TYPE)

    def test_cdf_rawtime_to_datetime_epoch16_scalar(self):
        source = self._get_random_epoch16()
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_to_datetime(None, source, CDF_EPOCH16_TYPE)

    def test_cdf_rawtime_to_datetime_tt2000_scalar(self):
        source = self._get_random_tt2000()
        expected = cdf_tt2000_to_utc_datetime(source)
        self._test_cdf_rawtime_to_datetime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_datetime_to_cdf_rawtime_epoch_array(self):
        source = self._get_random_datetime(10)
        expected = vectorize(utc_datetime_to_cdf_epoch, otypes=('float64',))(source)
        self._test_datetime_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_datetime_to_cdf_rawtime_epoch16_array(self):
        source = self._get_random_datetime(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_datetime_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_datetime_to_cdf_rawtime_tt2000_array(self):
        source = self._get_random_datetime(10)
        expected = vectorize(utc_datetime_to_cdf_tt2000, otypes=('int64',))(source)
        self._test_datetime_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_cdf_rawtime_to_datetime_epoch_array(self):
        source = self._get_random_epoch(10)
        expected = vectorize(cdf_epoch_to_utc_datetime, otypes=('object',))(source)
        self._test_cdf_rawtime_to_datetime(expected, source, CDF_EPOCH_TYPE)

    def test_cdf_rawtime_to_datetime_epoch16_array(self):
        source = self._get_random_epoch16(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_to_datetime(None, source, CDF_EPOCH16_TYPE)

    def test_cdf_rawtime_to_datetime_tt2000_array(self):
        source = self._get_random_tt2000(10)
        expected = vectorize(cdf_tt2000_to_utc_datetime, otypes=('object',))(source)
        self._test_cdf_rawtime_to_datetime(expected, source, CDF_TIME_TT2000_TYPE)

# -----------------------------------------------------------------------------

class TestDatetime64CDFTimeConversions(BaseCDFTimeConversionTest):
    """ Conversions between CDF times and numpy.datetime64 values
    """

    @classmethod
    def _get_random_datetime64(cls, unit, size=None):

        return asarray(randint(
            int64(datetime64(cls.start, unit)),
            int64(datetime64(cls.end, unit)),
            size=size, dtype="int64",
        )).astype(f"datetime64[{unit}]")

    def _test_datetime64_to_cdf_rawtime(self, expected, *args):
        self._test(expected, datetime64_to_cdf_rawtime, *args)

    def _test_cdf_rawtime_to_datetime64(self, expected, *args):
        self._test(expected, cdf_rawtime_to_datetime64, *args)

    def test_datetime64_to_cdf_rawtime_epoch_ns(self):
        source = self._get_random_datetime64("ns", 10)
        expected = utc_datetime64_us_to_cdf_epoch(source)
        self._test_datetime64_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_datetime64_to_cdf_rawtime_epoch16_ns(self):
        source = self._get_random_datetime64("ns", 10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_datetime64_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_datetime64_to_cdf_rawtime_tt2000_ns(self):
        source = self._get_random_datetime64("ns", 10)
        expected = utc_datetime64_ns_to_cdf_tt2000(source)
        self._test_datetime64_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_datetime64_to_cdf_rawtime_epoch_us(self):
        source = self._get_random_datetime64("us", 10)
        expected = utc_datetime64_us_to_cdf_epoch(source)
        self._test_datetime64_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_datetime64_to_cdf_rawtime_epoch16_us(self):
        source = self._get_random_datetime64("us", 10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_datetime64_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_datetime64_to_cdf_rawtime_tt2000_us(self):
        source = self._get_random_datetime64("us", 10)
        expected = utc_datetime64_ns_to_cdf_tt2000(source)
        self._test_datetime64_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_datetime64_to_cdf_rawtime_epoch_ms(self):
        source = self._get_random_datetime64("ms", 10)
        expected = utc_datetime64_us_to_cdf_epoch(source)
        self._test_datetime64_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_datetime64_to_cdf_rawtime_epoch16_ms(self):
        source = self._get_random_datetime64("ms", 10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_datetime64_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_datetime64_to_cdf_rawtime_tt2000_ms(self):
        source = self._get_random_datetime64("ms", 10)
        expected = utc_datetime64_ns_to_cdf_tt2000(source)
        self._test_datetime64_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_cdf_rawtime_to_datetime64_epoch(self):
        source = self._get_random_epoch(10)
        expected = cdf_epoch_to_utc_datetime64_us(source)
        self._test_cdf_rawtime_to_datetime64(expected, source, CDF_EPOCH_TYPE)

    def test_cdf_rawtime_to_datetime64_epoch16(self):
        source = self._get_random_epoch16(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_to_datetime64(None, source, CDF_EPOCH16_TYPE)

    def test_cdf_rawtime_to_datetime64_tt2000(self):
        source = self._get_random_tt2000(10)
        expected = cdf_tt2000_to_utc_datetime64_ns(source)
        self._test_cdf_rawtime_to_datetime64(expected, source, CDF_TIME_TT2000_TYPE)

# -----------------------------------------------------------------------------

class TestMJD2000CDFTimeConversions(BaseCDFTimeConversionTest):
    """ Conversions between CDF times and MJD2000 values
    """
    DT_2000 = datetime(2000, 1, 1)

    @classmethod
    def _get_random_mjd2000(cls, size=None):
        return uniform(
            float((cls.start - cls.DT_2000).days),
            float((cls.end - cls.DT_2000).days),
            size=size,
        )

    def _test_mjd2000_to_cdf_rawtime(self, expected, *args):
        self._test(expected, mjd2000_to_cdf_rawtime, *args)

    def _test_cdf_rawtime_to_mjd2000(self, expected, *args):
        self._test(expected, cdf_rawtime_to_mjd2000, *args)

    def test_mjd2000_to_cdf_rawtime_epoch(self):
        source = self._get_random_mjd2000(10)
        expected = mjd2000_to_cdf_epoch(source)
        self._test_mjd2000_to_cdf_rawtime(expected, source, CDF_EPOCH_TYPE)

    def test_mjd2000_to_cdf_rawtime_epoch16(self):
        source = self._get_random_mjd2000(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_mjd2000_to_cdf_rawtime(None, source, CDF_EPOCH16_TYPE)

    def test_mjd2000_to_cdf_rawtime_tt2000(self):
        source = self._get_random_mjd2000(10)
        expected = mjd2000_to_cdf_tt2000(source)
        self._test_mjd2000_to_cdf_rawtime(expected, source, CDF_TIME_TT2000_TYPE)

    def test_cdf_rawtime_to_mjd2000_epoch(self):
        source = self._get_random_epoch(10)
        expected = cdf_epoch_to_mjd2000(source)
        self._test_cdf_rawtime_to_mjd2000(expected, source, CDF_EPOCH_TYPE)

    def test_cdf_rawtime_to_mjd2000_epoch16(self):
        source = self._get_random_epoch16(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_to_mjd2000(None, source, CDF_EPOCH16_TYPE)

    def test_cdf_rawtime_to_mjd2000_tt2000(self):
        source = self._get_random_tt2000(10)
        expected = cdf_tt2000_to_mjd2000(source)
        self._test_cdf_rawtime_to_mjd2000(expected, source, CDF_TIME_TT2000_TYPE)

# -----------------------------------------------------------------------------

class TestUnixEpochCDFTimeConversions(BaseCDFTimeConversionTest):
    """ Conversions between CDF times and Unix epoch values
    """

    def _test_cdf_rawtime_to_unix_epoch(self, expected, *args):
        self._test(expected, cdf_rawtime_to_unix_epoch, *args)

    def test_cdf_rawtime_to_unix_epoch_epoch(self):
        source = self._get_random_epoch(10)
        expected = cdf_epoch_to_unix_epoch(source)
        self._test_cdf_rawtime_to_unix_epoch(expected, source, CDF_EPOCH_TYPE)

    def test_cdf_rawtime_to_unix_epoch_epoch16(self):
        source = self._get_random_epoch16(10)
        with self.assertRaises(UnsupportedCDFTimeTypeError):
            self._test_cdf_rawtime_to_unix_epoch(None, source, CDF_EPOCH16_TYPE)

    def test_cdf_rawtime_to_unix_epoch_tt2000(self):
        source = self._get_random_tt2000(10)
        expected = cdf_tt2000_to_unix_epoch(source)
        self._test_cdf_rawtime_to_unix_epoch(expected, source, CDF_TIME_TT2000_TYPE)

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
