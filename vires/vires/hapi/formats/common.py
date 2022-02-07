#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - common subroutines
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

from numpy import prod, datetime_data, asarray, timedelta64, char, choose, isnat

# These numpy.datetime64 format, when printed, have no time component.
DATE_ONLY_UNITS = set(["Y", "M", "W", "D"])

DATETIME64_TIEBREAK = {
    "h": timedelta64(30, "m"),
    "m": timedelta64(30, "s"),
    "s": timedelta64(5, "100ms"),
    "ms": timedelta64(5, "100us"),
    "us": timedelta64(5, "100ns"),
}


def convert_arrays(arrays, type_conversions):
    """ Convert arrays by type. """

    def _dummy_conversion(array):
        return array

    return [
        (type_conversions.get(array.dtype.type) or _dummy_conversion)(array)
        for array in arrays
    ]


def encode_string_array(array, encoding='UTF-8', bytes_per_char=4):
    """ Encode unicode string array to bytes using the requested encoding. """
    size = (array.dtype.itemsize >> 2) * bytes_per_char
    return char.encode(array, encoding).astype(f"S{size}")


def format_datetime64_array(array):
    """ Convert numpy.datetime64 array to a ASCII byte-string array."""
    string_size = len(str(asarray(0, array.dtype)))
    time_unit = datetime_data(array.dtype)[0]
    if time_unit == "Y":
        # there seems to be a bug in numpy 1.19:
        #  datetime64(0, 'Y').astype("U4") -> '197' with dtype "S3"
        #  datetime64(0, 'Y').astype("U5") -> '1970' with dtype "S4"
        string_array = array.astype(f"S5").astype(f"S{string_size}")
    else:
        string_array = array.astype(f"S{string_size}")
    if time_unit not in DATE_ONLY_UNITS:
        string_array = char.add(string_array, choose(isnat(array), [b'Z', b'']))
    return string_array


def format_datetime64_value(value):
    """ Convert numpy.datetime64 value to a string. """
    append_timezone = not isnat(value) and has_timezone(value.dtype)
    return f"{value}Z" if append_timezone else f"{value}"


def get_datetime64_string_size(type_):
    """ Get byte-size of a numpy.datetime64 timestamp. """
    string_size = len(str(asarray(0, type_)))
    return string_size + int(has_timezone(type_))


def has_timezone(type_):
    """ True if the datetime64 precision has time with a time-zone. """
    time_unit = datetime_data(type_)[0]
    return time_unit not in DATE_ONLY_UNITS


def round_datetime64(data, precision, tiebreak=None):
    """ Round numpy.datetime64 data to the desired precision. """
    if tiebreak is None:
        tiebreak = DATETIME64_TIEBREAK[precision]
    return (data + tiebreak).astype(f"datetime64[{precision}]")


def cast_datetime64(data, precision):
    """ Truncate numpy.datetime64 data to the desired precision. """
    return data.astype(f"datetime64[{precision}]")


def flatten_records(data, order="C"):
    """ Flatten or expand nD array into a 2D (row, record) array. """
    size, *shape = data.shape
    return data.reshape((size, prod(shape or 1)), order=order)
