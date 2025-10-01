#-------------------------------------------------------------------------------
#
# JSON input time parsers - tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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


from unittest import main, TestCase
from numpy import empty
from numpy.testing import assert_almost_equal
from vires.parsers.time.json_time_parser import (
    iso_datetime_to_mjd2000,
    array_iso_datetime_to_mjd2000,
    array_unix_epoch_to_mjd2000,
    array_decimal_year_to_mjd2000,
    array_cdf_epoch_to_mjd2000,
    array_cdf_tt2000_to_mjd2000,
    array_datetime64_to_mjd2000,
)

class TestISODatetimeParser(TestCase):

    def test_simple_timestamp(self):
        self.assertAlmostEqual(
            iso_datetime_to_mjd2000("2000-01-01T00:00:00.000000Z"), 0.0
        )

    def test_invalid_input_value(self):
        with self.assertRaises(ValueError):
            iso_datetime_to_mjd2000("X")

    def test_invalid_input_type(self):
        with self.assertRaises(TypeError):
            iso_datetime_to_mjd2000(None)

    def test_empty_array(self):
        assert_almost_equal(
            array_iso_datetime_to_mjd2000([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_almost_equal(
            array_iso_datetime_to_mjd2000("2000-01-01T00:00:00.000000Z"),
            0.0
        )

    def test_array(self):
        assert_almost_equal(
            array_iso_datetime_to_mjd2000([
                "2000-01-01T00:00:00.000000Z",
                "2001-01-01T00:00:00.000000Z",
                "2024-01-01T00:00:00.000000Z",
            ]),
            [0.0, 366.0, 8766.0]
        )


class TestUnixEpochParser(TestCase):

    def test_empty_array(self):
        assert_almost_equal(
            array_unix_epoch_to_mjd2000([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_almost_equal(
            array_unix_epoch_to_mjd2000(946684800.0),
            0.0
        )

    def test_array(self):
        assert_almost_equal(
            array_unix_epoch_to_mjd2000([
                946684800.0, 978307200.0, 1704067200.0,
            ]),
            [0.0, 366.0, 8766.0]
        )


class TestDecimalYearParser(TestCase):

    def test_empty_array(self):
        assert_almost_equal(
            array_decimal_year_to_mjd2000([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_almost_equal(
            array_decimal_year_to_mjd2000(2000.0),
            0.0
        )

    def test_array(self):
        assert_almost_equal(
            array_decimal_year_to_mjd2000([
                2000.0, 2001.0, 2024.0,
            ]),
            [0.0, 366.0, 8766.0]
        )


class TestCdfEpochYearParser(TestCase):

    def test_empty_array(self):
        assert_almost_equal(
            array_cdf_epoch_to_mjd2000([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_almost_equal(
            array_cdf_epoch_to_mjd2000(63113904000000.000),
            0.0
        )

    def test_array(self):
        assert_almost_equal(
            array_cdf_epoch_to_mjd2000([
                63113904000000.000,
                63145526400000.000,
                63871286400000.000,
            ]),
            [0.0, 366.0, 8766.0]
        )


class TestCdfTt2000YearParser(TestCase):

    def test_empty_array(self):
        assert_almost_equal(
            array_cdf_tt2000_to_mjd2000([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_almost_equal(
            array_cdf_tt2000_to_mjd2000(-43135816000000),
            0.0
        )

    def test_array(self):
        assert_almost_equal(
            array_cdf_tt2000_to_mjd2000([
                -43135816000000,
                31579264184000000,
                757339269184000000,
            ]),
            [0.0, 366.0, 8766.0]
        )


class TestDatetime64Parser(TestCase):

    def test_empty_array_s(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("s")([]),
            empty((0,), dtype="float64")
        )

    def test_empty_array_ms(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("ms")([]),
            empty((0,), dtype="float64")
        )

    def test_empty_array_us(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("us")([]),
            empty((0,), dtype="float64")
        )

    def test_empty_array_ns(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("ns")([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array_s(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("s")(946684800),
            0.0
        )

    def test_scalar_array_ms(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("ms")(946684800000),
            0.0
        )

    def test_scalar_array_us(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("us")(946684800000000),
            0.0
        )

    def test_scalar_array_ns(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("ns")(946684800000000000),
            0.0
        )

    def test_array_s(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("s")([
                946684800,
                978307200,
                1704067200,
            ]),
            [0.0, 366.0, 8766.0]
        )

    def test_array_ms(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("ms")([
                946684800000,
                978307200000,
                1704067200000,
            ]),
            [0.0, 366.0, 8766.0]
        )

    def test_array_us(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("us")([
                946684800000000,
                978307200000000,
                1704067200000000,
            ]),
            [0.0, 366.0, 8766.0]
        )

    def test_array_ns(self):
        assert_almost_equal(
            array_datetime64_to_mjd2000("ns")([
                946684800000000000,
                978307200000000000,
                1704067200000000000,
            ]),
            [0.0, 366.0, 8766.0]
        )


if __name__ == "__main__":
    main()
