#-------------------------------------------------------------------------------
#
#  VirES data-type structure
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
# pylint: disable=missing-docstring,unused-argument,too-few-public-methods

import re
from numpy import dtype

TIME_PRECISION = {
    None: "ms", # default
    "year": "Y",
    "month": "M",
    "day": "D",
    "hour": "h",
    "minute": "m",
    "second": "s",
    "millisecond": "ms",
    "microsecond": "us",
}

RE_DATA_TYPE = re.compile("([a-z]+)([1-9][0-9]*)?")


def parse_data_type(parameter_options):
    """ VirES parameter's data type parser. """
    data_type = parameter_options['dataType']

    match = RE_DATA_TYPE.match(data_type)

    if match:
        type_, size = match.groups()
        size = None if size is None else int(size)

        if type_ == TimestampDataType.type:
            return TimestampDataType(parameter_options.get("timePrecision"))

        if size in (NumberDataType.NUMBER_TYPES.get(type_) or ()):
            return NumberDataType(type_, size)

        if type_ in StringDataType.STRING_TYPES:
            return StringDataType(type_, size)

    raise ValueError(f"Unsupported data type {data_type}!")


class DataTypeBase():
    """ Base data type. """

    def __init__(self, type_string):
        self.type_string = type_string
        self.dtype = dtype(type_string)


class TimestampDataType(DataTypeBase):
    type = "timestamp"
    byte_size = 8
    bit_size = 64
    storage_type = "int64"
    epoch = "1970-01-01T00:00:00Z"
    standard = "UTC"

    def __init__(self, precision):
        self.unit = TIME_PRECISION[precision]
        super().__init__(f"datetime64[{self.unit}]")


class StringDataType(DataTypeBase):

    STRING_TYPES = {
        "char": ("ASCII", 1, 'S'),
        "unicode": ("UTF8", 4, 'U'),
    }

    def __init__(self, type_, size):
        encoding, item_size, np_type = self.STRING_TYPES[type_]
        self.type = type_
        self.byte_size = item_size * size
        self.encoding = encoding
        super().__init__(f"{np_type}{size}")


class NumberDataType(DataTypeBase):

    NUMBER_TYPES = {
        "uint": (8, 16, 32, 64),
        "int": (8, 16, 32, 64),
        "float": (32, 64),
    }

    def __init__(self, type_, size):
        super().__init__(f"{type_}{size}")
        self.type = type_
        self.byte_size = size >> 3
        self.bit_size = size
