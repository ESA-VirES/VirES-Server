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

from numpy import prod, datetime_data, asarray, timedelta64

# These numpy.datetime64 format, when printed, have no time component.
DATE_ONLY_UNITS = set(["Y", "M", "W", "D"])

DATETIME64_TIEBREAK = {
    "h": timedelta64(30, "m"),
    "m": timedelta64(30, "s"),
    "s": timedelta64(5, "100ms"),
    "ms": timedelta64(5, "100us"),
    "us": timedelta64(5, "100ns"),
}

def format_datetime64(value):
    """ Convert numpy.datetime64 value to a string. """
    return f"{value}" if datetime_data(value.dtype)[0] in DATE_ONLY_UNITS else f"{value}Z"


def get_datetime64_string_size(type_):
    """ Get byte-size of a numpy.datetime64 timestamp. """
    return len(format_datetime64(asarray(0, type_)))


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
