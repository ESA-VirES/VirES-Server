#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - common subroutines - tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=missing-docstring

from unittest import TestCase, main
from numpy import datetime64, dtype
from numpy.random import random
from numpy.testing import assert_equal
from vires.hapi.formats.common import (
    flatten_records,
    format_datetime64,
    get_datetime64_string_size,
    cast_datetime64,
    round_datetime64,
)

class TestDatetime64Rouding(TestCase):

    def _test_cast_datetime(self, input_, precision, expected_output, **kwargs):
        output = round_datetime64(input_, precision, **kwargs)
        assert_equal(output, expected_output)
        assert_equal(output.dtype, expected_output.dtype)

    def test_day_to_microsecond(self):
        self._test_cast_datetime(datetime64("2000", "D"), "us", datetime64("2000", "us"))

    def test_100nanseconds_to_microseconds(self):
        self._test_cast_datetime(
            datetime64("2000-01-01T00:00:00.0000000005", "100ns"), "us",
            datetime64("2000-01-01T00:00:00.000000001", "us")
        )

    def test_microsecond_to_millisecond(self):
        self._test_cast_datetime(
            datetime64("2000-01-01T00:00:00.0000005", "us"), "ms",
            datetime64("2000-01-01T00:00:00.000001", "ms")
        )

    def test_millisecond_to_second(self):
        self._test_cast_datetime(
            datetime64("2000-01-01T00:00:00.5", "ms"), "s",
            datetime64("2000-01-01T00:00:01", "s")
        )

    def test_second_to_minute(self):
        self._test_cast_datetime(
            datetime64("2000-01-01T00:00:30", "s"), "m",
            datetime64("2000-01-01T00:01:00", "m")
        )

    def test_minute_to_hour(self):
        self._test_cast_datetime(
            datetime64("2000-01-01T00:30", "m"), "h",
            datetime64("2000-01-01T01:00", "h")
        )


class TestDatetime64Cast(TestCase):

    def _test_cast_datetime(self, input_, precision, expected_output):
        output = cast_datetime64(input_, precision)
        assert_equal(output, expected_output)
        assert_equal(output.dtype, expected_output.dtype)

    def test_day_to_millisecond(self):
        self._test_cast_datetime(datetime64("2000", "D"), "ms", datetime64("2000", "ms"))

    def test_microsecond_to_second(self):
        self._test_cast_datetime(
            datetime64("1999-01-01T23:59:59.999999", "us"), "s",
            datetime64("1999-01-01T23:59:59.000000", "s")
        )

    def test_microsecond_to_10microseconds(self):
        self._test_cast_datetime(
            datetime64("1999-01-01T23:59:59.999999", "us"), "s",
            datetime64("1999-01-01T23:59:59.000000", "s")
        )


class TestDatetime64StringSize(TestCase):

    def _test_get_datetime64_string_size(self, input_, expected_output):
        self.assertEqual(get_datetime64_string_size(input_), expected_output)

    def test_year(self):
        self._test_get_datetime64_string_size(dtype("datetime64[Y]"), 4)

    def test_month(self):
        self._test_get_datetime64_string_size(dtype("datetime64[M]"), 7)

    def test_day(self):
        self._test_get_datetime64_string_size(dtype("datetime64[D]"), 10)

    def test_hour(self):
        self._test_get_datetime64_string_size(dtype("datetime64[h]"), 14)

    def test_minute(self):
        self._test_get_datetime64_string_size(dtype("datetime64[m]"), 17)

    def test_second(self):
        self._test_get_datetime64_string_size(dtype("datetime64[s]"), 20)

    def test_millisecond(self):
        self._test_get_datetime64_string_size(dtype("datetime64[ms]"), 24)

    def test_microsecond(self):
        self._test_get_datetime64_string_size(dtype("datetime64[us]"), 27)

    def test_nanosecond(self):
        self._test_get_datetime64_string_size(dtype("datetime64[ns]"), 30)


class TestDatetime64Formatting(TestCase):

    def _test_format_datetime64(self, input_, expected_output):
        self.assertEqual(format_datetime64(input_), expected_output)

    def test_year(self):
        self._test_format_datetime64(datetime64(0, "Y"), "1970")

    def test_month(self):
        self._test_format_datetime64(datetime64(0, "M"), "1970-01")

    def test_day(self):
        self._test_format_datetime64(datetime64(0, "D"), "1970-01-01")

    def test_hour(self):
        self._test_format_datetime64(datetime64(0, "h"), "1970-01-01T00Z")

    def test_minute(self):
        self._test_format_datetime64(datetime64(0, "m"), "1970-01-01T00:00Z")

    def test_second(self):
        self._test_format_datetime64(datetime64(0, "s"), "1970-01-01T00:00:00Z")

    def test_millisecond(self):
        self._test_format_datetime64(datetime64(0, "ms"), "1970-01-01T00:00:00.000Z")

    def test_microsecond(self):
        self._test_format_datetime64(datetime64(0, "us"), "1970-01-01T00:00:00.000000Z")

    def test_nanosecond(self):
        self._test_format_datetime64(datetime64(0, "ns"), "1970-01-01T00:00:00.000000000Z")


class TestFlattenRecords(TestCase):

    def _test_flatten_records(self, input_shape, output_shape):
        input_ = random(input_shape)
        expected_output = input_.reshape(output_shape, order="C")
        assert_equal(flatten_records(input_), expected_output)

    def test_1d_array(self):
        self._test_flatten_records(10, (10, 1))

    def test_2d_array(self):
        self._test_flatten_records((10, 5), (10, 5))

    def test_3d_array(self):
        self._test_flatten_records((10, 5, 3), (10, 15))

    def test_4d_array(self):
        self._test_flatten_records((10, 5, 3, 2), (10, 30))


if __name__ == "__main__":
    main()
