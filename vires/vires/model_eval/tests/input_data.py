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
import json
from numpy import array, empty
from numpy.testing import assert_equal
from vires.model_eval.input_data import (
    FORMAT_SPECIFIC_TIME_FORMAT,
    convert_json_input,
    convert_msgpack_input,
    convert_csv_input,
    convert_cdf_input,
    convert_hdf_input,
)
from vires.model_eval.common import (
    get_max_data_shape,
    check_shape_compatibility,
)
from vires.model_eval.calculation import (
    reshape_input_data,
)
from data import (
    INPUT_JSON_ISO_TIME,
    INPUT_JSON_MJD2000,
    INPUT_JSON_CDF_EPOCH,
    INPUT_MSGPK_ISO_TIME,
    INPUT_MSGPK_MJD2000,
    INPUT_MSGPK_CDF_EPOCH,
    INPUT_CSV_ISO_TIME,
    INPUT_CSV_MJD2000,
    INPUT_CSV_CDF_EPOCH,
    INPUT_CDF_CDF_EPOCH,
    INPUT_HDF_ISO_TIME,
    INPUT_HDF_DT64_US_TIME,
    INPUT_HDF_DT64_NS_TIME,
)


TEST_DATA_01 = {
    'MJD2000': array([0.0, 3653.0, 9132.0]),
    'Latitude': array([-45.0, 0.0, 45.0]),
    'Longitude': array([ 90.0, 0.0, -90.0]),
    'Radius': array([6380000.0, 6500000.0, 7000000.0]),
}

TEST_INPUT_TIMES_01 = {
    "ISO date-time": array(["2000-01-01T00:00Z", "2010-01-01T00:00Z", "2025-01-01T00:00Z"]),
    "CDF_EPOCH": array([63113904000000.0, 63429523200000.0, 63902908800000.0]),
    "MJD2000": array([0.0, 3653.0, 9132.0]),
    "datetime64[us]": array([946684800000000, 1262304000000000, 1735689600000000]),
    "datetime64[ns]": array([946684800000000000, 1262304000000000000, 1735689600000000000]),
}

CDF_OPTIONS = {
    "filename_prefix": "_temp_test_cdf_input",
    "filename_suffix": ".cdf",
    "temp_path": "/tmp",
}

HDF_OPTIONS = {
    "filename_prefix": "_temp_test_hdf_input",
    "filename_suffix": ".hdf5",
    "temp_path": "/tmp",
}

class ShapeOpTest(TestCase):

    def _test_max_shape(self, input_, expected_output):
        output = get_max_data_shape(input_)
        self.assertTrue(isinstance(output, tuple))
        self.assertEqual(output, expected_output)

    def _test_shape_compatibility(self, shape1, shape2, expected_output):
        output = check_shape_compatibility(shape1, shape2)
        if expected_output:
            self.assertTrue(output)
        else:
            self.assertFalse(output)

    def test_max_shape_empty(self):
        self._test_max_shape([(2, 3, 4), ()], (2, 3, 4))
        self._test_max_shape([(), (2, 3, 4)], (2, 3, 4))

    def test_max_shape_mixed_sizes(self):
        self._test_max_shape([(2, 3, 4), (2, 3)], (2, 3, 4))
        self._test_max_shape([(2, 3), (2, 3, 4)], (2, 3, 4))

    def test_max_shape_mixed_dims(self):
        self._test_max_shape([(2, 1, 4), (1, 3)], (2, 3, 4))
        self._test_max_shape([(1, 3), (2, 1, 4)], (2, 3, 4))

    def test_shapes_equal(self):
        self._test_shape_compatibility((2, 3, 4), (2, 3, 4), True)

    def test_shapes_empty(self):
        self._test_shape_compatibility((2, 3, 4), (), True)
        self._test_shape_compatibility((), (2, 3, 4), True)

    def test_shapes_mixed_sizes(self):
        self._test_shape_compatibility((2, 3, 4), (2, 3), True)
        self._test_shape_compatibility((2, 3), (2, 3, 4), True)

    def test_shapes_broadcasted(self):
        self._test_shape_compatibility((2, 1, 4), (1, 3), True)
        self._test_shape_compatibility((1, 3), (2, 1, 4), True)

    def test_shapes_incompatible(self):
        self._test_shape_compatibility((2, 3, 4), (3, 2), False)
        self._test_shape_compatibility((3, 3), (2, 3, 4), False)

    def _test_reshape_input_data(
        self, time_shape, lats_shape, lons_shape, rads_shape,
        expected_time_shape, expected_coords_shape
    ):
        times, coords = reshape_input_data(
            empty(time_shape),
            empty(lats_shape),
            empty(lons_shape),
            empty(rads_shape)
        )
        self.assertEqual(times.shape, expected_time_shape)
        self.assertEqual(coords.shape, expected_coords_shape)

    def test_reshape_input_data_equal(self):
        self._test_reshape_input_data(
            (2, 3), (2, 3), (2, 3), (2, 3),
            (2, 3), (2, 3, 3),
        )

    def test_reshape_input_data_scalar_time_and_radius(self):
        self._test_reshape_input_data(
            (), (2, 3), (2, 3), (),
            (), (2, 3, 3),
        )

    def test_reshape_input_data_multi_time_and_radius(self):
        self._test_reshape_input_data(
            (5,), (1, 1, 3, 2), (1, 1, 3, 2), (1, 4),
            (5,), (5, 4, 3, 2, 3),
        )


class InputDataTest(TestCase):

    def test_input_json_iso_time_default(self):
        with open(INPUT_JSON_ISO_TIME, "rb") as file:
            data, time_format = convert_json_input(json.load(file), FORMAT_SPECIFIC_TIME_FORMAT)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_json_iso_time(self):
        with open(INPUT_JSON_ISO_TIME, "rb") as file:
            data, time_format = convert_json_input(json.load(file), "ISO date-time")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_json_mjd2000(self):
        with open(INPUT_JSON_MJD2000, "rb") as file:
            data, time_format = convert_json_input(json.load(file), "MJD2000")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["MJD2000"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "MJD2000")

    def test_input_json_cdf_epoch(self):
        with open(INPUT_JSON_CDF_EPOCH, "rb") as file:
            data, time_format = convert_json_input(json.load(file), "CDF_EPOCH")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["CDF_EPOCH"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "CDF_EPOCH")

    def test_input_msgpack_iso_time_default(self):
        with open(INPUT_MSGPK_ISO_TIME, "rb") as file:
            data, time_format = convert_msgpack_input(file, FORMAT_SPECIFIC_TIME_FORMAT)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_msgpack_iso_time(self):
        with open(INPUT_MSGPK_ISO_TIME, "rb") as file:
            data, time_format = convert_msgpack_input(file, "ISO date-time")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_msgpack_mjd2000(self):
        with open(INPUT_MSGPK_MJD2000, "rb") as file:
            data, time_format = convert_msgpack_input(file, "MJD2000")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["MJD2000"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "MJD2000")

    def test_input_msgpack_cdf_epoch(self):
        with open(INPUT_MSGPK_CDF_EPOCH, "rb") as file:
            data, time_format = convert_msgpack_input(file, "CDF_EPOCH")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["CDF_EPOCH"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "CDF_EPOCH")

    def test_input_csv_iso_time_default(self):
        with open(INPUT_CSV_ISO_TIME, "r", encoding="utf-8") as file:
            data, time_format = convert_csv_input(file, FORMAT_SPECIFIC_TIME_FORMAT)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_csv_iso_time(self):
        with open(INPUT_CSV_ISO_TIME, "r", encoding="utf-8") as file:
            data, time_format = convert_csv_input(file, "ISO date-time")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_csv_mjd2000(self):
        with open(INPUT_CSV_MJD2000, "r", encoding="utf-8") as file:
            data, time_format = convert_csv_input(file, "MJD2000")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["MJD2000"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "MJD2000")

    def test_input_csv_cdf_epoch(self):
        with open(INPUT_CSV_CDF_EPOCH, "r", encoding="utf-8") as file:
            data, time_format = convert_csv_input(file, "CDF_EPOCH")
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["CDF_EPOCH"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "CDF_EPOCH")

    def test_input_cdf_cdf_epoch_default(self):
        with open(INPUT_CDF_CDF_EPOCH, "rb") as file:
            data, time_format = convert_cdf_input(file, FORMAT_SPECIFIC_TIME_FORMAT, **CDF_OPTIONS)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["CDF_EPOCH"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "CDF_EPOCH")

    def test_input_cdf_cdf_epoch(self):
        with open(INPUT_CDF_CDF_EPOCH, "rb") as file:
            data, time_format = convert_cdf_input(file, "CDF_EPOCH", **CDF_OPTIONS)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["CDF_EPOCH"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "CDF_EPOCH")

    def test_input_hdf_iso_time_default(self):
        with open(INPUT_HDF_ISO_TIME, "rb") as file:
            data, time_format = convert_hdf_input(file, FORMAT_SPECIFIC_TIME_FORMAT, **HDF_OPTIONS)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_hdf_iso_time(self):
        with open(INPUT_HDF_ISO_TIME, "rb") as file:
            data, time_format = convert_hdf_input(file, "ISO date-time", **HDF_OPTIONS)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["ISO date-time"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "ISO date-time")

    def test_input_hdf_dt64_ns(self):
        with open(INPUT_HDF_DT64_NS_TIME, "rb") as file:
            data, time_format = convert_hdf_input(file, "datetime64[ns]", **HDF_OPTIONS)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["datetime64[ns]"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "datetime64[ns]")

    def test_input_hdf_dt64_us(self):
        with open(INPUT_HDF_DT64_US_TIME, "rb") as file:
            data, time_format = convert_hdf_input(file, "datetime64[us]", **HDF_OPTIONS)
        expected_data = {**TEST_DATA_01, "_Timestamp": TEST_INPUT_TIMES_01["datetime64[us]"]}
        assert_equal(data, expected_data)
        self.assertEqual(time_format, "datetime64[us]")


if __name__ == "__main__":
    main()
