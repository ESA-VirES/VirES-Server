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
from numpy import array
from numpy.testing import assert_equal
from vires.model_eval.input_data import (
    FORMAT_SPECIFIC_TIME_FORMAT,
    convert_json_input,
    convert_msgpack_input,
    convert_csv_input,
    convert_cdf_input,
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
)


TEST_DATA_01 = {
    'MJD2000': array([0.0, 3653.0, 9132.0]),
    'Latitude': array([-45.0, 0.0, 45.0]),
    'Longitude': array([ 90.0, 0.0, -90.0]),
    'Radius': array([6380000.0, 6500000.0, 7000000.0]),
}

CDF_OPTIONS = {
    "filename_prefix": "_temp_test_cdf_input",
    "filename_suffix": ".cdf",
    "temp_path": "/tmp",
}


class InputDataTest(TestCase):

    def test_input_json_iso_time_default(self):
        with open(INPUT_JSON_ISO_TIME, "rb") as file:
            data = convert_json_input(json.load(file), FORMAT_SPECIFIC_TIME_FORMAT)
        assert_equal(data, TEST_DATA_01)

    def test_input_json_iso_time(self):
        with open(INPUT_JSON_ISO_TIME, "rb") as file:
            data = convert_json_input(json.load(file), "ISO date-time")
        assert_equal(data, TEST_DATA_01)

    def test_input_json_mjd2000(self):
        with open(INPUT_JSON_MJD2000, "rb") as file:
            data = convert_json_input(json.load(file), "MJD2000")
        assert_equal(data, TEST_DATA_01)

    def test_input_json_cdf_epoch(self):
        with open(INPUT_JSON_CDF_EPOCH, "rb") as file:
            data = convert_json_input(json.load(file), "CDF_EPOCH")
        assert_equal(data, TEST_DATA_01)


    def test_input_msgpack_iso_time_default(self):
        with open(INPUT_MSGPK_ISO_TIME, "rb") as file:
            data = convert_msgpack_input(file, FORMAT_SPECIFIC_TIME_FORMAT)
        assert_equal(data, TEST_DATA_01)

    def test_input_msgpack_iso_time(self):
        with open(INPUT_MSGPK_ISO_TIME, "rb") as file:
            data = convert_msgpack_input(file, "ISO date-time")
        assert_equal(data, TEST_DATA_01)

    def test_input_msgpack_mjd2000(self):
        with open(INPUT_MSGPK_MJD2000, "rb") as file:
            data = convert_msgpack_input(file, "MJD2000")
        assert_equal(data, TEST_DATA_01)

    def test_input_msgpack_cdf_epoch(self):
        with open(INPUT_MSGPK_CDF_EPOCH, "rb") as file:
            data = convert_msgpack_input(file, "CDF_EPOCH")
        assert_equal(data, TEST_DATA_01)


    def test_input_csv_iso_time_default(self):
        with open(INPUT_CSV_ISO_TIME, "r", encoding="utf-8") as file:
            data = convert_csv_input(file, FORMAT_SPECIFIC_TIME_FORMAT)
        assert_equal(data, TEST_DATA_01)

    def test_input_csv_iso_time(self):
        with open(INPUT_CSV_ISO_TIME, "r", encoding="utf-8") as file:
            data = convert_csv_input(file, "ISO date-time")
        assert_equal(data, TEST_DATA_01)

    def test_input_csv_mjd2000(self):
        with open(INPUT_CSV_MJD2000, "r", encoding="utf-8") as file:
            data = convert_csv_input(file, "MJD2000")
        assert_equal(data, TEST_DATA_01)

    def test_input_csv_cdf_epoch(self):
        with open(INPUT_CSV_CDF_EPOCH, "r", encoding="utf-8") as file:
            data = convert_csv_input(file, "CDF_EPOCH")
        assert_equal(data, TEST_DATA_01)


    def test_input_cdf_cdf_epoch_default(self):
        with open(INPUT_CDF_CDF_EPOCH, "rb") as file:
            data = convert_cdf_input(file, FORMAT_SPECIFIC_TIME_FORMAT, **CDF_OPTIONS)
        assert_equal(data, TEST_DATA_01)

    def test_input_cdf_cdf_epoch(self):
        with open(INPUT_CDF_CDF_EPOCH, "rb") as file:
            data = convert_cdf_input(file, "CDF_EPOCH", **CDF_OPTIONS)
        assert_equal(data, TEST_DATA_01)


if __name__ == "__main__":
    main()
