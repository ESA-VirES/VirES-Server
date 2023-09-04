#-------------------------------------------------------------------------------
#
# Leap seconds table - tests
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
# pylint: disable=missing-docstring,line-too-long

from unittest import TestCase, main
from collections import namedtuple
from numpy import array, arange, datetime64, int64
from numpy.testing import assert_equal
from vires.leap_seconds import LEAP_NANOSECONDS_TABLE, NANOSECONDS_PER_DAY

DT64_2000 = datetime64("2000-01-01T00:00:00", "ns")


class LeapNanosecondsTableTest(TestCase):
    table = LEAP_NANOSECONDS_TABLE

    def _get_test_times(self):
        return arange(
            int64(datetime64("1950-01-01", "ns") - DT64_2000),
            int64(datetime64("2050-01-01", "ns") - DT64_2000),
            NANOSECONDS_PER_DAY,
        )

    def test_forward_and_reverse_conversions_day_start(self):
        utc2000ns = self._get_test_times()
        offset_utc = self.table.get_tai_offset_for_utc2000ns(utc2000ns)
        offset_tai = self.table.get_tai_offset_for_tai2000ns(utc2000ns + offset_utc)
        assert_equal(offset_utc, offset_tai)

    def test_forward_and_reverse_conversions_midday(self):
        utc2000ns = self._get_test_times() + NANOSECONDS_PER_DAY // 2
        offset_utc = self.table.get_tai_offset_for_utc2000ns(utc2000ns)
        offset_tai = self.table.get_tai_offset_for_tai2000ns(utc2000ns + offset_utc)
        assert_equal(offset_utc, offset_tai)


    def test_forward_and_reverse_conversions_day_end_nonnegative_leap(self):
        utc2000ns = self._get_test_times()
        offset_utc_day_start = self.table.get_tai_offset_for_utc2000ns(utc2000ns)
        offset_utc_day_end = self.table.get_tai_offset_for_utc2000ns(utc2000ns - 1)
        offset_tai_day_end = self.table.get_tai_offset_for_tai2000ns(utc2000ns - 1 + offset_utc_day_end)

        leaps = offset_utc_day_start - offset_utc_day_end
        nonnegative_leaps = leaps >= 0

        assert_equal(
            offset_utc_day_end[nonnegative_leaps],
            offset_tai_day_end[nonnegative_leaps],
        )

        assert_equal(
            offset_utc_day_end[~nonnegative_leaps],
            offset_tai_day_end[~nonnegative_leaps] - leaps[~nonnegative_leaps],
        )

    def test_forward_and_reverse_conversions_day_end_nonpositive_leap(self):
        utc2000ns = self._get_test_times()
        tai2000ns = utc2000ns + self.table.get_tai_offset_for_utc2000ns(utc2000ns)
        offset_tai_day_start = self.table.get_tai_offset_for_tai2000ns(tai2000ns)
        offset_tai_day_end = self.table.get_tai_offset_for_tai2000ns(tai2000ns - 1)

        offset_utc_day_end = self.table.get_tai_offset_for_utc2000ns(tai2000ns - 1 - offset_tai_day_end)

        leaps = offset_tai_day_start - offset_tai_day_end
        nonpositive_leaps = leaps <= 0

        assert_equal(
            offset_tai_day_end[nonpositive_leaps],
            offset_utc_day_end[nonpositive_leaps],
        )

        assert_equal(
            offset_tai_day_end[~nonpositive_leaps],
            offset_utc_day_end[~nonpositive_leaps] - leaps[~nonpositive_leaps],
        )

    def test_leap_seconds(self):

        def _time(date_string):
            return int64(datetime64(date_string, "ns") - DT64_2000)

        DataPair = namedtuple("DataPair", ["time", "offset"])

        values = [
            DataPair(_time("1960-01-01") - 1, 0),
            DataPair(_time("1960-01-01"), 944130000),
            DataPair(_time("1966-01-01") - 1, 4312522000),
            DataPair(_time("1966-01-01"), 4314466000),
            DataPair(_time("1972-01-01") - 1, 9890946000),
            DataPair(_time("1972-01-01"), 10000000000),
            DataPair(_time("1972-07-01") - 1, 10000000000),
            DataPair(_time("1972-07-01"), 11000000000),
            DataPair(_time("1973-01-01") - 1, 11000000000),
            DataPair(_time("1973-01-01"), 12000000000),
            DataPair(_time("1974-01-01") - 1, 12000000000),
            DataPair(_time("1974-01-01"), 13000000000),
            DataPair(_time("1975-01-01") - 1, 13000000000),
            DataPair(_time("1975-01-01"), 14000000000),
            DataPair(_time("1976-01-01") - 1, 14000000000),
            DataPair(_time("1976-01-01"), 15000000000),
            DataPair(_time("1977-01-01") - 1, 15000000000),
            DataPair(_time("1977-01-01"), 16000000000),
            DataPair(_time("1978-01-01") - 1, 16000000000),
            DataPair(_time("1978-01-01"), 17000000000),
            DataPair(_time("1979-01-01") - 1, 17000000000),
            DataPair(_time("1979-01-01"), 18000000000),
            DataPair(_time("1980-01-01") - 1, 18000000000),
            DataPair(_time("1980-01-01"), 19000000000),
            DataPair(_time("1981-07-01") - 1, 19000000000),
            DataPair(_time("1981-07-01"), 20000000000),
            DataPair(_time("1982-07-01") - 1, 20000000000),
            DataPair(_time("1982-07-01"), 21000000000),
            DataPair(_time("1983-07-01") - 1, 21000000000),
            DataPair(_time("1983-07-01"), 22000000000),
            DataPair(_time("1985-07-01") - 1, 22000000000),
            DataPair(_time("1985-07-01"), 23000000000),
            DataPair(_time("1988-01-01") - 1, 23000000000),
            DataPair(_time("1988-01-01"), 24000000000),
            DataPair(_time("1990-01-01") - 1, 24000000000),
            DataPair(_time("1990-01-01"), 25000000000),
            DataPair(_time("1991-01-01") - 1, 25000000000),
            DataPair(_time("1991-01-01"), 26000000000),
            DataPair(_time("1992-07-01") - 1, 26000000000),
            DataPair(_time("1992-07-01"), 27000000000),
            DataPair(_time("1993-07-01") - 1, 27000000000),
            DataPair(_time("1993-07-01"), 28000000000),
            DataPair(_time("1994-07-01") - 1, 28000000000),
            DataPair(_time("1994-07-01"), 29000000000),
            DataPair(_time("1996-01-01") - 1, 29000000000),
            DataPair(_time("1996-01-01"), 30000000000),
            DataPair(_time("1997-07-01") - 1, 30000000000),
            DataPair(_time("1997-07-01"), 31000000000),
            DataPair(_time("1999-01-01") - 1, 31000000000),
            DataPair(_time("1999-01-01"), 32000000000),
            DataPair(_time("2006-01-01") - 1, 32000000000),
            DataPair(_time("2006-01-01"), 33000000000),
            DataPair(_time("2009-01-01") - 1, 33000000000),
            DataPair(_time("2009-01-01"), 34000000000),
            DataPair(_time("2012-07-01") - 1, 34000000000),
            DataPair(_time("2012-07-01"), 35000000000),
            DataPair(_time("2015-07-01") - 1, 35000000000),
            DataPair(_time("2015-07-01"), 36000000000),
            DataPair(_time("2017-01-01") - 1, 36000000000),
            DataPair(_time("2017-01-01"), 37000000000),
        ]

        utc2000ns = array([item.time for item in values])
        tested_offsets = self.table.get_tai_offset_for_utc2000ns(utc2000ns)
        expected_offsets = array([item.offset for item in values])

        assert_equal(expected_offsets, tested_offsets)


if __name__ == "__main__":
    main()
