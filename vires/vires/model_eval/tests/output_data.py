#-------------------------------------------------------------------------------
#
# Evaluation of magnetic models at user provided times and locations
# - output data handling tests
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
from os import remove
from os.path import exists
import json
import msgpack
import h5py
from numpy import asarray, char
from numpy.testing import assert_equal
from vires.cdf_util import cdf_open
from vires.model_eval.output_data import (
    FORMAT_SPECIFIC_TIME_FORMAT,
    TIME_KEY,
    MJD2000_KEY,
    BACKUP_TIME_KEY,
    LOCATION_KEYS,
    JSON_DEFAULT_TIME_FORMAT,
    CSV_DEFAULT_TIME_FORMAT,
    MSGP_DEFAULT_TIME_FORMAT,
    CDF_DEFAULT_TIME_FORMAT,
    HDF_DEFAULT_TIME_FORMAT,
    enforce_1d_data_shape,
    write_json_output,
    write_msgpack_output,
    write_csv_output,
    write_cdf_output,
    write_hdf_output,
    write_sources,
)

TEST_DATA_01 = {
    'MJD2000': asarray([0.0, 3653.0, 9132.0]),
    'Latitude': asarray([-45.0, 0.0, 45.0]),
    'Longitude': asarray([ 90.0, 0.0, -90.0]),
    'Radius': asarray([6380000.0, 6500000.0, 7000000.0]),
    'B_Model1': asarray([[1.9, 2.8, 3.7], [4.6, 5.5, 6.4], [7.3, 8.2, 9.1]]),
    'B_Model2': asarray([[7.3, 8.2, 9.1], [4.6, 5.5, 6.4], [1.9, 2.8, 3.7]]),
}

TEST_TIMES_01 = {
    "ISO date-time": asarray(["2000-01-01T00:00Z", "2010-01-01T00:00Z", "2025-01-01T00:00Z"]),
    "CDF_EPOCH": asarray([63113904000000.0, 63429523200000.0, 63902908800000.0]),
    "CDF_TIME_TT2000": asarray([-43135816000000, 315576066184000000, 788961669184000000]),
    "MJD2000": asarray([0.0, 3653.0, 9132.0]),
    "datetime64[us]": asarray([946684800000000, 1262304000000000, 1735689600000000]),
    "datetime64[ns]": asarray([946684800000000000, 1262304000000000000, 1735689600000000000]),
}

TEST_CONVERTED_TIMES_01 = {
    "ISO date-time": asarray(["2000-01-01T00:00:00.000Z", "2010-01-01T00:00:00.000Z", "2025-01-01T00:00:00.000Z"]),
    "CDF_EPOCH": asarray([63113904000000.0, 63429523200000.0, 63902908800000.0]),
    "CDF_TIME_TT2000": asarray([-43135816000000, 315576066184000000, 788961669184000000]),
    "MJD2000": asarray([0.0, 3653.0, 9132.0]),
    "datetime64[us]": asarray([946684800000000, 1262304000000000, 1735689600000000]),
    "datetime64[ns]": asarray([946684800000000000, 1262304000000000000, 1735689600000000000]),
}

MODEL_INFO_01 = {
    "Model1": {
        "name": "Model1",
        "expression": "MODEL01()",
        "sources": [
            "SOURCE2",
            "SOURCE1",
        ]
    },
    "Model2": {
        "name": "Model2",
        "expression": "MODEL02()",
        "sources": [
            "SOURCE3",
            "SOURCE2",
        ]
    },
}

MODEL_SOURCES_01 = ["SOURCE1", "SOURCE2", "SOURCE3"]
MODEL_LIST_01 = ["Model1 = MODEL01()", "Model2 = MODEL02()"]


class SourcesWriterTest(TestCase):

    def _read_sources(self, buffer):
        buffer.seek(0)
        return [
            line.strip("\r\n")
            for line in buffer
        ]

    def test_source_writer(self):
        self.assertEqual(
            self._read_sources(write_sources(MODEL_INFO_01)),
            MODEL_SOURCES_01
        )


class JsonWriterTest(TestCase):

    def _test_json(self, output_time_format, input_time_format):
        resolved_output_time_format = (
            JSON_DEFAULT_TIME_FORMAT
            if output_time_format == FORMAT_SPECIFIC_TIME_FORMAT else
            output_time_format
        )
        input_data = {
            **TEST_DATA_01,
            "_Timestamp": TEST_TIMES_01[input_time_format],
        }
        expected_data = {
            "Timestamp": (
                TEST_TIMES_01
                if input_time_format == resolved_output_time_format else
                TEST_CONVERTED_TIMES_01
            )[resolved_output_time_format].tolist(),
            **{
                key: values.tolist()
                for key, values in TEST_DATA_01.items()
                if key != "MJD2000"
            },
            "__info__": {"models": MODEL_INFO_01},
        }
        data = write_json_output(
            input_data, output_time_format, input_time_format, MODEL_INFO_01,
        )
        assert_equal(data, expected_data)

    def test_json_def_iso(self):
        self._test_json(FORMAT_SPECIFIC_TIME_FORMAT, "ISO date-time")

    def test_json_def_mjd(self):
        self._test_json(FORMAT_SPECIFIC_TIME_FORMAT, "MJD2000")

    def test_json_def_cdf(self):
        self._test_json(FORMAT_SPECIFIC_TIME_FORMAT, "CDF_EPOCH")

    def test_json_iso_iso(self):
        self._test_json("ISO date-time", "ISO date-time")

    def test_json_iso_mjd(self):
        self._test_json("ISO date-time", "MJD2000")

    def test_json_iso_cdf(self):
        self._test_json("ISO date-time", "CDF_EPOCH")

    def test_json_mjd_iso(self):
        self._test_json("MJD2000", "ISO date-time")

    def test_json_mjd_mjd(self):
        self._test_json("MJD2000", "MJD2000")

    def test_json_mjd_cdf(self):
        self._test_json("MJD2000", "CDF_EPOCH")

    def test_json_cdf_iso(self):
        self._test_json("CDF_EPOCH", "ISO date-time")

    def test_json_cdf_mjd(self):
        self._test_json("CDF_EPOCH", "MJD2000")

    def test_json_cdf_cdf(self):
        self._test_json("CDF_EPOCH", "CDF_EPOCH")

    def test_json_tt2k_iso(self):
        self._test_json("CDF_TIME_TT2000", "ISO date-time")

    def test_json_tt2k_mjd(self):
        self._test_json("CDF_TIME_TT2000", "MJD2000")

    def test_json_tt2k_cdf(self):
        self._test_json("CDF_TIME_TT2000", "CDF_EPOCH")

    def test_json_tt2k_tt2k(self):
        self._test_json("CDF_TIME_TT2000", "CDF_TIME_TT2000")

    def test_json_dt64_ns_iso(self):
        self._test_json("datetime64[ns]", "ISO date-time")

    def test_json_dt64_ns_mjd(self):
        self._test_json("datetime64[ns]", "MJD2000")

    def test_json_dt64_ns_cdf(self):
        self._test_json("datetime64[ns]", "CDF_EPOCH")

    def test_json_dt64_ns_dt64_ns(self):
        self._test_json("datetime64[ns]", "datetime64[ns]")


class MsgpackWriterTest(TestCase):

    def _read_msgpack(self, buffer):
        buffer.seek(0)
        return msgpack.load(buffer)

    def _test_msgpack(self, output_time_format, input_time_format):
        resolved_output_time_format = (
            MSGP_DEFAULT_TIME_FORMAT
            if output_time_format == FORMAT_SPECIFIC_TIME_FORMAT else
            output_time_format
        )
        input_data = {
            **TEST_DATA_01,
            "_Timestamp": TEST_TIMES_01[input_time_format],
        }
        expected_data = {
            "Timestamp": (
                TEST_TIMES_01
                if input_time_format == resolved_output_time_format else
                TEST_CONVERTED_TIMES_01
            )[resolved_output_time_format].tolist(),
            **{
                key: values.tolist()
                for key, values in TEST_DATA_01.items()
                if key != "MJD2000"
            },
            "__info__": {"models": MODEL_INFO_01},
        }
        data = self._read_msgpack(
            write_msgpack_output(
                input_data, output_time_format, input_time_format, MODEL_INFO_01
            )
        )
        assert_equal(data, expected_data)

    def test_msgpack_def_iso(self):
        self._test_msgpack(FORMAT_SPECIFIC_TIME_FORMAT, "ISO date-time")

    def test_msgpack_def_mjd(self):
        self._test_msgpack(FORMAT_SPECIFIC_TIME_FORMAT, "MJD2000")

    def test_msgpack_def_cdf(self):
        self._test_msgpack(FORMAT_SPECIFIC_TIME_FORMAT, "CDF_EPOCH")

    def test_msgpack_iso_iso(self):
        self._test_msgpack("ISO date-time", "ISO date-time")

    def test_msgpack_iso_mjd(self):
        self._test_msgpack("ISO date-time", "MJD2000")

    def test_msgpack_iso_cdf(self):
        self._test_msgpack("ISO date-time", "CDF_EPOCH")

    def test_msgpack_mjd_iso(self):
        self._test_msgpack("MJD2000", "ISO date-time")

    def test_msgpack_mjd_mjd(self):
        self._test_msgpack("MJD2000", "MJD2000")

    def test_msgpack_mjd_cdf(self):
        self._test_msgpack("MJD2000", "CDF_EPOCH")

    def test_msgpack_cdf_iso(self):
        self._test_msgpack("CDF_EPOCH", "ISO date-time")

    def test_msgpack_cdf_mjd(self):
        self._test_msgpack("CDF_EPOCH", "MJD2000")

    def test_msgpack_cdf_cdf(self):
        self._test_msgpack("CDF_EPOCH", "CDF_EPOCH")

    def test_msgpack_tt2k_iso(self):
        self._test_msgpack("CDF_TIME_TT2000", "ISO date-time")

    def test_msgpack_tt2k_mjd(self):
        self._test_msgpack("CDF_TIME_TT2000", "MJD2000")

    def test_msgpack_tt2k_cdf(self):
        self._test_msgpack("CDF_TIME_TT2000", "CDF_EPOCH")

    def test_msgpack_tt2k_tt2k(self):
        self._test_msgpack("CDF_TIME_TT2000", "CDF_TIME_TT2000")

    def test_msgpack_dt64_ns_iso(self):
        self._test_msgpack("datetime64[ns]", "ISO date-time")

    def test_msgpack_dt64_ns_mjd(self):
        self._test_msgpack("datetime64[ns]", "MJD2000")

    def test_msgpack_dt64_ns_cdf(self):
        self._test_msgpack("datetime64[ns]", "CDF_EPOCH")

    def test_msgpack_dt64_ns_dt64_ns(self):
        self._test_msgpack("datetime64[ns]", "datetime64[ns]")


class CsvWriterTest(TestCase):

    def _read_csv(self, buffer):
        buffer.seek(0)
        lines = iter(buffer)
        keys = next(lines).strip("\r\n").split(",")
        data = {key: [] for key in keys}
        for line  in lines:
            values = line.strip("\r\n").split(",")
            for key, value in zip(keys, values):
                data[key].append(self._parse_csv_value(value))
        return data

    @staticmethod
    def _parse_csv_value(value):

        value = value.strip()

        if not value:
            return value

        if (value[0], value[-1]) == ("{", "}"):
            return [float(v) for v in value[1:-1].split(";")]

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return float(value)
        except ValueError:
            pass

        return value

    def _test_csv(self, output_time_format, input_time_format):
        resolved_output_time_format = (
            CSV_DEFAULT_TIME_FORMAT
            if output_time_format == FORMAT_SPECIFIC_TIME_FORMAT else
            output_time_format
        )
        input_data = {
            **TEST_DATA_01,
            "_Timestamp": TEST_TIMES_01[input_time_format],
        }
        expected_data = {
            "Timestamp": (
                TEST_TIMES_01
                if input_time_format == resolved_output_time_format else
                TEST_CONVERTED_TIMES_01
            )[resolved_output_time_format].tolist(),
            **{
                key: values.tolist()
                for key, values in TEST_DATA_01.items()
                if key != "MJD2000"
            }
        }
        data = self._read_csv(
            write_csv_output(
                input_data, output_time_format, input_time_format, MODEL_INFO_01
            )
        )
        assert_equal(data, expected_data)

    def test_csv_def_iso(self):
        self._test_csv(FORMAT_SPECIFIC_TIME_FORMAT, "ISO date-time")

    def test_csv_def_mjd(self):
        self._test_csv(FORMAT_SPECIFIC_TIME_FORMAT, "MJD2000")

    def test_csv_def_cdf(self):
        self._test_csv(FORMAT_SPECIFIC_TIME_FORMAT, "CDF_EPOCH")

    def test_csv_iso_iso(self):
        self._test_csv("ISO date-time", "ISO date-time")

    def test_csv_iso_mjd(self):
        self._test_csv("ISO date-time", "MJD2000")

    def test_csv_iso_cdf(self):
        self._test_csv("ISO date-time", "CDF_EPOCH")

    def test_csv_mjd_iso(self):
        self._test_csv("MJD2000", "ISO date-time")

    def test_csv_mjd_mjd(self):
        self._test_csv("MJD2000", "MJD2000")

    def test_csv_mjd_cdf(self):
        self._test_csv("MJD2000", "CDF_EPOCH")

    def test_csv_cdf_iso(self):
        self._test_csv("CDF_EPOCH", "ISO date-time")

    def test_csv_cdf_mjd(self):
        self._test_csv("CDF_EPOCH", "MJD2000")

    def test_csv_cdf_cdf(self):
        self._test_csv("CDF_EPOCH", "CDF_EPOCH")

    def test_csv_tt2k_iso(self):
        self._test_csv("CDF_TIME_TT2000", "ISO date-time")

    def test_csv_tt2k_mjd(self):
        self._test_csv("CDF_TIME_TT2000", "MJD2000")

    def test_csv_tt2k_cdf(self):
        self._test_csv("CDF_TIME_TT2000", "CDF_EPOCH")

    def test_csv_tt2k_tt2k(self):
        self._test_csv("CDF_TIME_TT2000", "CDF_TIME_TT2000")

    def test_csv_dt64_ns_iso(self):
        self._test_csv("datetime64[ns]", "ISO date-time")

    def test_csv_dt64_ns_mjd(self):
        self._test_csv("datetime64[ns]", "MJD2000")

    def test_csv_dt64_ns_cdf(self):
        self._test_csv("datetime64[ns]", "CDF_EPOCH")

    def test_csv_dt64_ns_dt64_ns(self):
        self._test_csv("datetime64[ns]", "datetime64[ns]")


class CdfWriterTest(TestCase):

    def _read_cdf(self, filename):
        try:
            with cdf_open(filename) as cdf:
                return (
                    {
                        key: cdf.raw_var(key)[...]
                        for key in cdf
                    },
                    list(cdf.attrs["SOURCES"]),
                    list(cdf.attrs["MAGNETIC_MODELS"]),
                )
        finally:
            if exists(filename):
                remove(filename)

    @staticmethod
    def _fix_strings(data):
        if data.dtype.char == "U":
            return char.encode(data, "ascii")
        return data

    def _test_cdf(self, output_time_format, input_time_format):
        resolved_output_time_format = (
            CDF_DEFAULT_TIME_FORMAT
            if output_time_format == FORMAT_SPECIFIC_TIME_FORMAT else
            output_time_format
        )
        input_data = {
            **TEST_DATA_01,
            "_Timestamp": TEST_TIMES_01[input_time_format],
        }
        expected_data = {
            "Timestamp": self._fix_strings((
                TEST_TIMES_01
                if input_time_format == resolved_output_time_format else
                TEST_CONVERTED_TIMES_01
            )[resolved_output_time_format]),
            **{
                key: values
                for key, values in TEST_DATA_01.items()
                if key != "MJD2000"
            }
        }
        data, sources, models = self._read_cdf(
            write_cdf_output(
                input_data, output_time_format, input_time_format, MODEL_INFO_01
            )
        )
        assert_equal(data, expected_data)
        self.assertEqual(sources, MODEL_SOURCES_01)
        self.assertEqual(models, MODEL_LIST_01)

    def test_cdf_def_iso(self):
        self._test_cdf(FORMAT_SPECIFIC_TIME_FORMAT, "ISO date-time")

    def test_cdf_def_mjd(self):
        self._test_cdf(FORMAT_SPECIFIC_TIME_FORMAT, "MJD2000")

    def test_cdf_def_cdf(self):
        self._test_cdf(FORMAT_SPECIFIC_TIME_FORMAT, "CDF_EPOCH")

    def test_cdf_iso_iso(self):
        self._test_cdf("ISO date-time", "ISO date-time")

    def test_cdf_iso_mjd(self):
        self._test_cdf("ISO date-time", "MJD2000")

    def test_cdf_iso_cdf(self):
        self._test_cdf("ISO date-time", "CDF_EPOCH")

    def test_cdf_mjd_iso(self):
        self._test_cdf("MJD2000", "ISO date-time")

    def test_cdf_mjd_mjd(self):
        self._test_cdf("MJD2000", "MJD2000")

    def test_cdf_mjd_cdf(self):
        self._test_cdf("MJD2000", "CDF_EPOCH")

    def test_cdf_cdf_iso(self):
        self._test_cdf("CDF_EPOCH", "ISO date-time")

    def test_cdf_cdf_mjd(self):
        self._test_cdf("CDF_EPOCH", "MJD2000")

    def test_cdf_cdf_cdf(self):
        self._test_cdf("CDF_EPOCH", "CDF_EPOCH")

    def test_cdf_tt2k_iso(self):
        self._test_cdf("CDF_TIME_TT2000", "ISO date-time")

    def test_cdf_tt2k_mjd(self):
        self._test_cdf("CDF_TIME_TT2000", "MJD2000")

    def test_cdf_tt2k_cdf(self):
        self._test_cdf("CDF_TIME_TT2000", "CDF_EPOCH")

    def test_cdf_tt2k_tt2k(self):
        self._test_cdf("CDF_TIME_TT2000", "CDF_TIME_TT2000")

    def test_cdf_dt64_ns_iso(self):
        self._test_cdf("datetime64[ns]", "ISO date-time")

    def test_cdf_dt64_ns_mjd(self):
        self._test_cdf("datetime64[ns]", "MJD2000")

    def test_cdf_dt64_ns_cdf(self):
        self._test_cdf("datetime64[ns]", "CDF_EPOCH")

    def test_cdf_dt64_ns_dt64_ns(self):
        self._test_cdf("datetime64[ns]", "datetime64[ns]")


class HdfWriterTest(TestCase):

    def _read_hdf(self, filename):
        try:
            with h5py.File(filename, "r") as hdf:
                return (
                    {
                        key: hdf[key][...]
                        for key in hdf
                    },
                    list(hdf.attrs["sources"]),
                    list(hdf.attrs["magnetic_models"]),
                )
        finally:
            if exists(filename):
                remove(filename)

    @staticmethod
    def _fix_strings(data):
        if data.dtype.char == "U":
            return char.encode(data, "ascii")
        return data

    def _test_hdf(self, output_time_format, input_time_format):
        resolved_output_time_format = (
            HDF_DEFAULT_TIME_FORMAT
            if output_time_format == FORMAT_SPECIFIC_TIME_FORMAT else
            output_time_format
        )
        input_data = {
            **TEST_DATA_01,
            "_Timestamp": TEST_TIMES_01[input_time_format],
        }
        expected_data = {
            "Timestamp": self._fix_strings((
                TEST_TIMES_01
                if input_time_format == resolved_output_time_format else
                TEST_CONVERTED_TIMES_01
            )[resolved_output_time_format]),
            **{
                key: values
                for key, values in TEST_DATA_01.items()
                if key != "MJD2000"
            }
        }
        data, sources, models = self._read_hdf(
            write_hdf_output(
                input_data, output_time_format, input_time_format, MODEL_INFO_01
            )
        )
        assert_equal(data, expected_data)
        self.assertEqual(sources, MODEL_SOURCES_01)
        self.assertEqual(models, MODEL_LIST_01)

    def test_hdf_def_iso(self):
        self._test_hdf(FORMAT_SPECIFIC_TIME_FORMAT, "ISO date-time")

    def test_hdf_def_mjd(self):
        self._test_hdf(FORMAT_SPECIFIC_TIME_FORMAT, "MJD2000")

    def test_hdf_def_cdf(self):
        self._test_hdf(FORMAT_SPECIFIC_TIME_FORMAT, "CDF_EPOCH")

    def test_hdf_def_dt64_us(self):
        self._test_hdf(FORMAT_SPECIFIC_TIME_FORMAT, "datetime64[us]")

    def test_hdf_def_dt64_ns(self):
        self._test_hdf(FORMAT_SPECIFIC_TIME_FORMAT, "datetime64[ns]")

    def test_hdf_iso_iso(self):
        self._test_hdf("ISO date-time", "ISO date-time")

    def test_hdf_iso_mjd(self):
        self._test_hdf("ISO date-time", "MJD2000")

    def test_hdf_iso_cdf(self):
        self._test_hdf("ISO date-time", "CDF_EPOCH")

    def test_hdf_iso_dt64_us(self):
        self._test_hdf("ISO date-time", "datetime64[us]")

    def test_hdf_iso_dt64_ns(self):
        self._test_hdf("ISO date-time", "datetime64[ns]")

    def test_hdf_mjd_iso(self):
        self._test_hdf("MJD2000", "ISO date-time")

    def test_hdf_mjd_mjd(self):
        self._test_hdf("MJD2000", "MJD2000")

    def test_hdf_mjd_cdf(self):
        self._test_hdf("MJD2000", "CDF_EPOCH")

    def test_hdf_mdj_dt64_us(self):
        self._test_hdf("MJD2000", "datetime64[us]")

    def test_hdf_mjd_dt64_ns(self):
        self._test_hdf("MJD2000", "datetime64[ns]")

    def test_hdf_cdf_iso(self):
        self._test_hdf("CDF_EPOCH", "ISO date-time")

    def test_hdf_cdf_mjd(self):
        self._test_hdf("CDF_EPOCH", "MJD2000")

    def test_hdf_cdf_cdf(self):
        self._test_hdf("CDF_EPOCH", "CDF_EPOCH")

    def test_hdf_cdf_dt64_us(self):
        self._test_hdf("CDF_EPOCH", "datetime64[us]")

    def test_hdf_cdf_dt64_ns(self):
        self._test_hdf("CDF_EPOCH", "datetime64[ns]")

    def test_hdf_tt2k_iso(self):
        self._test_hdf("CDF_TIME_TT2000", "ISO date-time")

    def test_hdf_tt2k_mjd(self):
        self._test_hdf("CDF_TIME_TT2000", "MJD2000")

    def test_hdf_tt2k_cdf(self):
        self._test_hdf("CDF_TIME_TT2000", "CDF_EPOCH")

    def test_hdf_tt2k_tt2k(self):
        self._test_hdf("CDF_TIME_TT2000", "CDF_TIME_TT2000")

    def test_hdf_tt2k_dt64_us(self):
        self._test_hdf("CDF_TIME_TT2000", "datetime64[us]")

    def test_hdf_tt2k_dt64_ns(self):
        self._test_hdf("CDF_TIME_TT2000", "datetime64[ns]")

    def test_hdf_dt64_us_iso(self):
        self._test_hdf("datetime64[us]", "ISO date-time")

    def test_hdf_dt64_us_mjd(self):
        self._test_hdf("datetime64[us]", "MJD2000")

    def test_hdf_dt64_us_cdf(self):
        self._test_hdf("datetime64[us]", "CDF_EPOCH")

    def test_hdf_dt64_us_dt64_us(self):
        self._test_hdf("datetime64[us]", "datetime64[us]")

    def test_hdf_dt64_us_dt64_ns(self):
        self._test_hdf("datetime64[us]", "datetime64[ns]")

    def test_hdf_dt64_ns_iso(self):
        self._test_hdf("datetime64[ns]", "ISO date-time")

    def test_hdf_dt64_ns_mjd(self):
        self._test_hdf("datetime64[ns]", "MJD2000")

    def test_hdf_dt64_ns_cdf(self):
        self._test_hdf("datetime64[ns]", "CDF_EPOCH")

    def test_hdf_dt64_ns_dt64_us(self):
        self._test_hdf("datetime64[ns]", "datetime64[us]")

    def test_hdf_dt64_ns_dt64_ns(self):
        self._test_hdf("datetime64[ns]", "datetime64[ns]")


class InputDataTest(TestCase):
    KEYS = [TIME_KEY, MJD2000_KEY, BACKUP_TIME_KEY, *LOCATION_KEYS]

    def test_0d_data(self):
        input_ = {
            key: asarray(1.0)
            for key in self.KEYS
        }
        expected_output = {
            key: asarray([1.0])
            for key in self.KEYS
        }
        data = enforce_1d_data_shape(input_)
        self.assertEqual(
            {key: value.shape for key, value in data.items()},
            {key: value.shape for key, value in expected_output.items()},
        )

    def test_0d_data_in_place(self):
        input_ = {
            key: asarray(1.0)
            for key in self.KEYS
        }
        expected_output = {
            key: asarray([1.0])
            for key in self.KEYS
        }
        enforce_1d_data_shape(input_)
        self.assertEqual(
            {key: value.shape for key, value in input_.items()},
            {key: value.shape for key, value in expected_output.items()},
        )

    def test_1d_data_in_place(self):
        input_ = {
            key: asarray([1.0, 2.0, 3.0])
            for key in self.KEYS
        }
        expected_output = {
            key: asarray([1.0, 2.0, 3.0])
            for key in self.KEYS
        }
        enforce_1d_data_shape(input_)
        self.assertEqual(
            {key: value.shape for key, value in input_.items()},
            {key: value.shape for key, value in expected_output.items()},
        )

    def test_2d_data_in_place(self):
        input_ = {
            key: asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
            for key in self.KEYS
        }
        with self.assertRaises(ValueError):
            enforce_1d_data_shape(input_)


if __name__ == "__main__":
    main()
