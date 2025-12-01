#-------------------------------------------------------------------------------
#
# Evaluation of magnetic models at user provided times and locations
# - input data handling
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

# TODO: NetCDF support

from collections import namedtuple
from shutil import copyfileobj
from tempfile import NamedTemporaryFile

from numpy import asarray
import msgpack

from vires.cdf_util import (
    cdf_open,
    CDF_EPOCH_TYPE,
    CDF_EPOCH16_TYPE,
    CDF_TIME_TT2000_TYPE,
)
from vires.readers import read_csv_data
from vires.parsers.time.json_time_parser import (
    array_iso_datetime_to_mjd2000,
    array_unix_epoch_to_mjd2000,
    array_decimal_year_to_mjd2000,
    array_cdf_epoch_to_mjd2000,
    array_cdf_tt2000_to_mjd2000,
    array_datetime64_to_mjd2000,
)

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

CHUNK_SIZE = 1024 * 1024 # 1MiB


INPUT_TIME_FORMATS = [
    "ISO date-time",
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

TIME_PARSERS = {
    "ISO date-time": array_iso_datetime_to_mjd2000,
    "MJD2000": lambda values: asarray(values, dtype="float64"),
    "Unix epoch": array_unix_epoch_to_mjd2000,
    "Decimal year": array_decimal_year_to_mjd2000,
    "CDF_EPOCH": array_cdf_epoch_to_mjd2000,
    "CDF_TIME_TT2000": array_cdf_tt2000_to_mjd2000,
    "datetime64[s]": array_datetime64_to_mjd2000("s"),
    "datetime64[ms]": array_datetime64_to_mjd2000("ms"),
    "datetime64[us]": array_datetime64_to_mjd2000("us"),
    "datetime64[ns]": array_datetime64_to_mjd2000("ns"),
}


def convert_json_input(data, time_format, time_key=TIME_KEY, location_keys=LOCATION_KEYS):
    """ Process JSON input data as returned by the json.load() function and
    convert it into a common data format.
    """
    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = JSON_DEFAULT_TIME_FORMAT
    time_parser = _get_time_parser("JSON", time_format, TIME_PARSERS)
    data = _convert_input_data(data, time_key, location_keys, time_parser)
    return data, time_format


def convert_msgpack_input(data_file, time_format, time_key=TIME_KEY,
                          location_keys=LOCATION_KEYS):
    """ Process MessagePack serialized input in form of a binary file-like
    object and convert it into a common data format.
    """
    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = MSGP_DEFAULT_TIME_FORMAT
    time_parser = _get_time_parser("MessagePack", time_format, TIME_PARSERS)
    data = msgpack.load(data_file)
    data = _convert_input_data(data, time_key, location_keys, time_parser)
    return data, time_format


def convert_csv_input(data_file, time_format, time_key=TIME_KEY,
                      location_keys=LOCATION_KEYS):
    """ Process CSV serialized input in form of a string sequence (or text
    file-like object).
    """
    if time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        time_format = CSV_DEFAULT_TIME_FORMAT
    time_parser = _get_time_parser("CSV", time_format, TIME_PARSERS)
    # parse input CSV and convert scalar number types
    data = read_csv_data(
        data_file,
        fields=[time_key, *location_keys],
        type_parsers = [int, float],
    )
    data = _convert_input_data(data, time_key, location_keys, time_parser)
    return data, time_format


def convert_cdf_input(data_file, time_format, time_key=TIME_KEY,
                      location_keys=LOCATION_KEYS,
                      filename_prefix="_temp_cdf_input",
                      filename_suffix=".cdf", temp_path=".",
                      chunk_size=CHUNK_SIZE):

    Record = namedtuple("Record", ["data", "cdf_type"])

    time_key = "Timestamp"
    location_keys = ["Latitude", "Longitude", "Radius"]

    # CDF requires writing of a temporary file and access by filename
    with NamedTemporaryFile(
        mode="wb", prefix=filename_prefix, suffix=filename_suffix,
        dir=temp_path, delete=True,
    ) as file:
        copyfileobj(data_file, file, chunk_size)
        file.flush()
        with cdf_open(file.name) as cdf:
            data = {
                key: Record(cdf_var[...], cdf_var.type())
                for key, cdf_var in (
                    (variable, cdf.raw_var(variable)) for variable in [
                        time_key, *location_keys
                    ]
                )
            }

    # handle native CDF time formats
    if data[time_key].cdf_type == CDF_EPOCH_TYPE:
        time_format = "CDF_EPOCH"
    elif data[time_key].cdf_type == CDF_TIME_TT2000_TYPE:
        time_format = "CDF_TIME_TT2000"
    elif data[time_key].cdf_type == CDF_EPOCH16_TYPE:
        raise ValueError("Unsupported CDF time format!")
    elif time_format == FORMAT_SPECIFIC_TIME_FORMAT:
        raise ValueError("Unexpected CDF time format!")
    time_parser = _get_time_parser("CDF", time_format, TIME_PARSERS)
    data = _convert_input_data(
        {key: record.data for key, record in data.items()},
        time_key, location_keys, time_parser
    )
    return data, time_format


def _get_time_parser(data_format_name, time_format, parsers):
    """ Resolve data-format specific time parser. """
    parser = parsers.get(time_format)
    if parser is None:
        raise ValueError(
            f"The {time_format} time format is not supported by the "
            f"{data_format_name} data format!"
        )
    return parser


def _convert_input_data(data, time_key, location_keys, time_parser,
                        target_time_key=MJD2000_KEY,
                        target_location_keys=LOCATION_KEYS,
                        backup_time_key=BACKUP_TIME_KEY):
    """ Convert input data into correctly typed arrays. """
    try:
        data = {
            target_time_key: time_parser(data[time_key]),
            **{
                target_key: asarray(data[key], "float64")
                for target_key, key in zip(target_location_keys, location_keys)
            },
            # preserve the original time values
            backup_time_key: asarray(data[time_key]),
        }
    except KeyError as error:
        raise ValueError(f"Missing mandatory {error} variable!") from None

    _enforce_compatible_dimenstions(data, target_time_key, target_location_keys)

    return data


def _enforce_compatible_dimenstions(data, time_key, location_keys):

    # FIXME: implement dimension broadcasting

    if data[location_keys[0]].shape != data[location_keys[1]].shape:
        raise ValueError(
            f"Dimension mismatch between {location_keys[0]} and "
            f"{location_keys[1]} location coordinates!"
        )

    if data[location_keys[0]].shape != data[location_keys[2]].shape:
        raise ValueError(
            f"Dimension mismatch between {location_keys[0]} and "
            f"{location_keys[2]} location coordinates!"
        )

    if data[location_keys[0]].shape != data[time_key].shape:
        raise ValueError("Dimension mismatch between location and times!")
