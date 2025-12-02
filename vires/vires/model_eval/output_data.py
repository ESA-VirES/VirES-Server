#-------------------------------------------------------------------------------
#
# Evaluation of magnetic models at user provided times and locations
# - output data handling
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
# pylint: disable=too-many-arguments,too-many-positional-arguments

# TODO: fix dependencies and move time conversion functions to a separate module

from os import remove
from os.path import join, exists
from uuid import uuid4
from io import BytesIO, StringIO
import msgpack
from numpy import asarray, timedelta64, datetime64, char
from eoxmagmod import mjd2000_to_decimal_year
from vires.time_util import mjd2000_to_unix_epoch
from vires.hapi.formats.common import format_datetime64_array
from vires.cdf_util import (
    cdf_open,
    CDF_CHAR_TYPE,
    CDF_EPOCH_TYPE,
    CDF_TIME_TT2000_TYPE,
    CDF_DOUBLE_TYPE,
    CDF_INT8_TYPE,
)
from vires.time_cdf_epoch import mjd2000_to_cdf_epoch
from vires.time_cdf_tt2000 import mjd2000_to_cdf_tt2000
from .common import (
    FORMAT_SPECIFIC_TIME_FORMAT,
    TIME_KEY,
    BACKUP_TIME_KEY,
    MJD2000_KEY,
    LOCATION_KEYS,
    JSON_DEFAULT_TIME_FORMAT,
    CSV_DEFAULT_TIME_FORMAT,
    MSGP_DEFAULT_TIME_FORMAT,
)

CDF_DEFAULT_TIME_FORMAT = "CDF_EPOCH"

OUTPUT_TIME_FORMATS = [
    "ISO date-time",
    "ISO date-time [s]",
    "ISO date-time [ms]",
    "ISO date-time [us]",
    "ISO date-time [ns]",
    "MJD2000",
    "Unix epoch",
    "Decimal year",
    "CDF_EPOCH",
    "CDF_TIME_TT2000",
    "datetime64[s]",
    "datetime64[ms]",
    "datetime64[us]",
    "datetime64[ns]",
    FORMAT_SPECIFIC_TIME_FORMAT,
]


def array_mjd2000_to_unix_epoch(values):
    """ Convert MJD2000 time values to array of unix-epoch timestamps. """
    return mjd2000_to_unix_epoch(asarray(values))


def array_mjd2000_to_datetime64(precision):
    """ Get conversion function from MJD2000 time values to datetime64 array
    with the given precision.
    """
    dtype_delta = f"timedelta64[{precision}]"
    zero_day = datetime64("2000-01-01", precision)
    units_per_day = timedelta64(1, "D").astype(dtype_delta).astype("int64")
    def _array_mjd2000_to_datetime64(values):
        return (
           asarray(values) * units_per_day
        ).round().astype(dtype_delta) + zero_day
    return _array_mjd2000_to_datetime64


def array_mjd2000_to_isoformat(precision):
    """ Get conversion function from MJD2000 time values to array of ISO
    formatted strings with the given precision.
    """
    _array_mjd2000_to_datetime64 = array_mjd2000_to_datetime64(precision)
    def _array_mjd2000_to_isoformat(values):
        return format_datetime64_array(_array_mjd2000_to_datetime64(values))
    return _array_mjd2000_to_isoformat


TIME_CONVERT = {
    "ISO date-time": array_mjd2000_to_isoformat("ms"),
    "ISO date-time [s]": array_mjd2000_to_isoformat("s"),
    "ISO date-time [ms]": array_mjd2000_to_isoformat("ms"),
    "ISO date-time [us]": array_mjd2000_to_isoformat("us"),
    "ISO date-time [ns]": array_mjd2000_to_isoformat("ns"),
    "MJD2000": asarray,
    "Unix epoch": array_mjd2000_to_unix_epoch,
    "Decimal year": mjd2000_to_decimal_year,
    "CDF_EPOCH": mjd2000_to_cdf_epoch,
    "CDF_TIME_TT2000": mjd2000_to_cdf_tt2000,
    "datetime64[s]": array_mjd2000_to_datetime64("s"),
    "datetime64[ms]": array_mjd2000_to_datetime64("ms"),
    "datetime64[us]": array_mjd2000_to_datetime64("us"),
    "datetime64[ns]": array_mjd2000_to_datetime64("ns"),
}


CDF_TIME_TYPE = {
    "ISO date-time": CDF_CHAR_TYPE,
    "ISO date-time [s]": CDF_CHAR_TYPE,
    "ISO date-time [ms]": CDF_CHAR_TYPE,
    "ISO date-time [us]": CDF_CHAR_TYPE,
    "ISO date-time [ns]": CDF_CHAR_TYPE,
    "MJD2000": CDF_DOUBLE_TYPE,
    "Unix epoch": CDF_DOUBLE_TYPE,
    "Decimal year": CDF_DOUBLE_TYPE,
    "CDF_EPOCH": CDF_EPOCH_TYPE,
    "CDF_TIME_TT2000": CDF_TIME_TT2000_TYPE,
    "datetime64[s]": CDF_INT8_TYPE,
    "datetime64[ms]": CDF_INT8_TYPE,
    "datetime64[us]": CDF_INT8_TYPE,
    "datetime64[ns]": CDF_INT8_TYPE,
    FORMAT_SPECIFIC_TIME_FORMAT: CDF_EPOCH_TYPE,
}


def enforce_1d_data_shape(
    data,
    time_key=TIME_KEY,
    mjd2000_key=MJD2000_KEY,
    backup_time_key=BACKUP_TIME_KEY,
    location_keys=LOCATION_KEYS,
):
    """ Enforce 1D data shape. """
    keys = [
        key for key in [time_key, mjd2000_key, backup_time_key, *location_keys]
        if key in data
    ]

    if not keys:
        return data

    max_ndim = max(data[key].ndim for key in keys)
    if max_ndim > 1:
        raise ValueError(
            "Number of data dimension too hight for the selected output format."
        )
    if max_ndim == 0:
        for key in keys:
            data[key].resize((1,))
    return data


def write_json_output(data, time_format, input_time_format, model_info):
    """ Convert output data to serializable output object. """
    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = JSON_DEFAULT_TIME_FORMAT
    time_convert = _get_time_convert("JSON", time_format, TIME_CONVERT)
    data = _covert_time_to_output_format(
        data, time_convert, time_format, input_time_format
    )
    data = _covert_ascii_arrays_to_unicode(data)
    data = _covert_arrays_to_lists(data)
    data["__info__"] = {"models": model_info}
    return data


def write_msgpack_output(data, time_format, input_time_format, model_info):
    """ Convert output data to MessagePack in-memory file. """
    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = MSGP_DEFAULT_TIME_FORMAT
    time_convert = _get_time_convert("MessagePack", time_format, TIME_CONVERT)
    data = _covert_time_to_output_format(
        data, time_convert, time_format, input_time_format
    )
    data = _covert_ascii_arrays_to_unicode(data)
    data = _covert_arrays_to_lists(data)
    data["__info__"] = {"models": model_info}
    return BytesIO(msgpack.dumps(data))


def write_csv_output(data, time_format, input_time_format, model_info):
    """ Convert output data to CSV in-memory file. """

    def _write_csv(file_obj, data):
        keys = list(data)
        formatters = [
            get_csv_value_formatter(data[key], precise=(key == TIME_KEY))
            for key in keys
        ]
        print(",".join(keys), file=file_obj)
        line_format = ",".join("{}" for _ in keys)
        for row in zip(*(data[key] for key in keys)):
            print(line_format.format(
                *(format_(value) for format_, value in zip(formatters, row))
            ), file=file_obj)
        return file_obj

    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = CSV_DEFAULT_TIME_FORMAT
    time_convert = _get_time_convert("CSV", time_format, TIME_CONVERT)
    data = _covert_time_to_output_format(
        data, time_convert, time_format, input_time_format
    )
    return _write_csv(StringIO(newline="\r\n"), data)


def get_csv_value_formatter(data, precise=False, encoding="ascii"):
    """ Second order function returning optimal data-type CSV string formatter
    function.
    """
    def _get_csv_value_formatter(shape, dtype):
        if len(shape) > 1:
            value_formater = _get_csv_value_formatter(shape[1:], dtype)
            def formater(arr):
                " vector formatter "
                return "{%s}" % ";".join(value_formater(value) for value in arr)
            return formater
        if dtype.char == "S":
            return lambda v: v.decode(encoding)
        if dtype.char == "d":
            if precise:
                return lambda v: "%.14g" % v
            return lambda v: "%.9g" % v
        return str
    return _get_csv_value_formatter(data.shape, data.dtype)


def write_cdf_output(data, time_format, input_time_format, model_info,
                     filename_prefix="_temp_cdf_output_",
                     filename_suffix=".cdf", temp_path="."):
    """ Convert output data to a CDF temporary file. """

    def _remove_existent(filename):
        if exists(filename):
            remove(filename)

    def _write_cdf(filename, data):
        _remove_existent(filename)
        try:
            with cdf_open(filename, "w") as cdf:
                for key, array in data.items():
                    cdf_type = CDF_TIME_TYPE[time_format] if key == TIME_KEY else CDF_DOUBLE_TYPE
                    itemsize = array.dtype.itemsize if cdf_type == CDF_CHAR_TYPE else 1
                    cdf.new(
                        name=key, data=array, type=cdf_type, n_elements=itemsize
                    )
                    #cdf[variable].attrs.update(
                    #    dataset.cdf_attr.get(variable, {})
                    #)
        except:
            _remove_existent(filename)
            raise

    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = CDF_DEFAULT_TIME_FORMAT
    time_convert = _get_time_convert("CDF", time_format, TIME_CONVERT)
    data = _covert_time_to_output_format(
        data, time_convert, time_format, input_time_format
    )
    filename = join(
        temp_path, f"{filename_prefix}{uuid4().hex}{filename_suffix}"
    )
    _write_cdf(filename, data)
    return filename


def write_sources(model_info):
    """  Convert model sources to an in-memory text file. """
    file_obj = StringIO(newline="\r\n")
    for source in _collect_sources(model_info):
        print(source, file=file_obj)
    return file_obj


def _collect_sources(model_info):
    return sorted(set(
        item
        for model in model_info.values()
        for item in model.get("sources") or ()
    ))


def _collect_model_expressions(model_info):
    return [
        f"{name} = {expression}".format(**model)
        for model in model_info.values()
    ]


def _covert_arrays_to_lists(data):
    return {key: array.tolist() for key, array in data.items()}


def _covert_ascii_arrays_to_unicode(data):
    return {
        key: char.decode(array, "ascii") if array.dtype.char == "S" else array
        for key, array in data.items()
    }


def _covert_time_to_output_format(
    data, convert_time, output_time_format, input_time_format,
    time_key=TIME_KEY, mjd2000_key=MJD2000_KEY, backup_time_key=BACKUP_TIME_KEY,
):
    if output_time_format == input_time_format:
        # copy preserved source time values
        output_time_values = data[backup_time_key]
    else:
        # convert MJD2000 times to the requested output format
        output_time_values = convert_time(data[mjd2000_key])

    excluded_keys = {mjd2000_key, backup_time_key}
    return {
        time_key: output_time_values,
        **{
            key: value
            for key, value in data.items()
            if key not in excluded_keys
        }
    }


def _get_time_convert(data_format_name, selected_format, converts):
    """ Resolve data-format specific time conversion function. """
    convert = converts.get(selected_format)
    if convert is None:
        raise ValueError(
            f"The {selected_format} time format is not supported by the "
            f"{data_format_name} data format!"
        )
    return convert
