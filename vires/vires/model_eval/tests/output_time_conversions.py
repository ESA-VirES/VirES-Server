#-------------------------------------------------------------------------------
#
# Evaluation of magnetic models at user provided times and locations
# - input data handling tests
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

from unittest import TestCase, main
from numpy import empty, asarray, datetime64
from numpy.testing import assert_equal
from vires.model_eval.output_data import (
    array_mjd2000_to_datetime64,
    array_mjd2000_to_isoformat,
    array_mjd2000_to_unix_epoch,
    mjd2000_to_decimal_year,
    mjd2000_to_cdf_epoch,
    mjd2000_to_cdf_tt2000,
)


class TestUnixEpochConversion(TestCase):

    def test_empty_array(self):
        assert_equal(
            array_mjd2000_to_unix_epoch([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_equal(
            array_mjd2000_to_unix_epoch(0.0),
            946684800.0
        )

    def test_array(self):
        assert_equal(
            array_mjd2000_to_unix_epoch([0.0, 366.0, 8766.0]),
            [946684800.0, 978307200.0, 1704067200.0]
        )


class TestDecimalYearConversion(TestCase):

    def test_empty_array(self):
        assert_equal(
            mjd2000_to_decimal_year([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_equal(
            mjd2000_to_decimal_year(0.0),
            2000.0
        )

    def test_array(self):
        assert_equal(
            mjd2000_to_decimal_year([0.0, 366.0, 8766.0]),
            [2000.0, 2001.0, 2024.0]
        )


class TestCdfEpochYearConversion(TestCase):

    def test_empty_array(self):
        assert_equal(
            mjd2000_to_cdf_epoch([]),
            empty((0,), dtype="float64")
        )

    def test_scalar_array(self):
        assert_equal(
            mjd2000_to_cdf_epoch(0.0),
            63113904000000.000,
        )

    def test_array(self):
        assert_equal(
            mjd2000_to_cdf_epoch([0.0, 366.0, 8766.0]),
            [
                63113904000000.000,
                63145526400000.000,
                63871286400000.000,
            ],
        )


class TestCdfTt2000YearConversion(TestCase):

    def test_empty_array(self):
        assert_equal(
            mjd2000_to_cdf_tt2000([]),
            empty((0,), dtype="int64")
        )

    def test_scalar_array(self):
        assert_equal(
            mjd2000_to_cdf_tt2000(0.0),
            -43135816000000
        )

    def test_array(self):
        assert_equal(
            mjd2000_to_cdf_tt2000([0.0, 366.0, 8766.0]),
            [
                -43135816000000,
                31579264184000000,
                757339269184000000,
            ]
        )


class TestMJD2000toDatetime64Conversion(TestCase):

    def _test_empty_array(self, precision):
        result = array_mjd2000_to_datetime64(precision)([])
        self.assertEqual(result.dtype, datetime64(0, precision).dtype)
        self.assertEqual(result.shape, (0,))
        assert_equal(result, empty((0,), dtype=f"datetime64[{precision}]"))

    def test_empty_array_s(self):
        self._test_empty_array("s")

    def test_empty_array_ms(self):
        self._test_empty_array("ms")

    def test_empty_array_us(self):
        self._test_empty_array("us")

    def test_empty_array_ns(self):
        self._test_empty_array("ns")

    def _test_scalar_array(self, precision):
        result = array_mjd2000_to_datetime64(precision)(0.0)
        self.assertEqual(result.dtype, datetime64(0, precision).dtype)
        self.assertEqual(result.shape, ())
        assert_equal(result, asarray("2000-01-01T00:00:00", dtype=f"datetime64[{precision}]"))

    def test_scalar_array_s(self):
        self._test_scalar_array("s")

    def test_scalar_array_ms(self):
        self._test_scalar_array("ms")

    def test_scalar_array_us(self):
        self._test_scalar_array("us")

    def test_scalar_array_ns(self):
        self._test_scalar_array("ns")

    def _test_array(self, precision):
        result = array_mjd2000_to_datetime64(precision)([0.0, 366.0, 8766.0])
        self.assertEqual(result.dtype, datetime64(0, precision).dtype)
        self.assertEqual(result.shape, (3,))
        assert_equal(result, asarray([
            "2000-01-01T00:00:00",
            "2001-01-01T00:00:00",
            "2024-01-01T00:00:00",
        ] , dtype=f"datetime64[{precision}]"))

    def test_array_s(self):
        self._test_array("s")

    def test_array_ms(self):
        self._test_array("ms")

    def test_array_us(self):
        self._test_array("us")

    def test_array_ns(self):
        self._test_array("ns")


class TestMJD2000toIsoFormat(TestCase):

    def _test_array(self, precision, source, desired):
        desired = asarray(desired)
        result = array_mjd2000_to_isoformat(precision)(source)
        assert_equal(result, desired)
        self.assertEqual(result.shape, desired.shape)

    def test_scalar_array_s(self):
        self._test_array("s", 0.0, b"2000-01-01T00:00:00Z")

    def test_scalar_array_ms(self):
        self._test_array("ms", 0.0, b"2000-01-01T00:00:00.000Z")

    def test_scalar_array_us(self):
        self._test_array("us", 0.0, b"2000-01-01T00:00:00.000000Z")

    def test_scalar_array_ns(self):
        self._test_array("ns", 0.0, b"2000-01-01T00:00:00.000000000Z")

    def test_array_s(self):
        self._test_array("s", [0.0, 366.0, 8766.0], [
            b"2000-01-01T00:00:00Z",
            b"2001-01-01T00:00:00Z",
            b"2024-01-01T00:00:00Z",
        ])

    def test_array_ms(self):
        self._test_array("ms", [0.0, 366.0, 8766.0], [
            b"2000-01-01T00:00:00.000Z",
            b"2001-01-01T00:00:00.000Z",
            b"2024-01-01T00:00:00.000Z",
        ])

    def test_array_us(self):
        self._test_array("us", [0.0, 366.0, 8766.0], [
            b"2000-01-01T00:00:00.000000Z",
            b"2001-01-01T00:00:00.000000Z",
            b"2024-01-01T00:00:00.000000Z",
        ])

    def test_array_ns(self):
        self._test_array("ns", [0.0, 366.0, 8766.0], [
            b"2000-01-01T00:00:00.000000000Z",
            b"2001-01-01T00:00:00.000000000Z",
            b"2024-01-01T00:00:00.000000000Z",
        ])


if __name__ == "__main__":
    main()
