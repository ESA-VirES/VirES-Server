#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - binary format subroutines
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

from itertools import chain
from struct import pack
from numpy import (
    asarray, str_, bytes_, bool_, float32, float64, datetime64,
    uint8, uint16, uint32, uint64, int8, int16, int32, int64,
)
from .common import (
    flatten_records, format_datetime64, get_datetime64_string_size,
)


# These numpy.datetime64 format, when printed, have no time component.
DATE_ONLY_UNITS = set(["Y", "M", "W", "D"])


def binary_encoder(format_):
    """ Build binary value encoder. """
    def _encoder(value, *_):
        return pack(format_, value)
    return _encoder


def trim_or_pad_bytes(byte_string, lenght):
    """ Trim or pad bytes to the requested byte length. """
    return byte_string[:lenght].ljust(lenght, b'\x00')


BINARY_ENCODING = {
    str_: lambda v, l: trim_or_pad_bytes(v.encode("utf8"), l),
    bytes_: trim_or_pad_bytes,
    bool_: binary_encoder("?"),
    int8: binary_encoder("b"),
    int16: binary_encoder("<h"),
    int32: binary_encoder("<l"),
    int64: binary_encoder("<q"),
    uint8: binary_encoder("B"),
    uint16: binary_encoder("<H"),
    uint32: binary_encoder("<L"),
    uint64: binary_encoder("<Q"),
    float32: binary_encoder("<f"),
    float64: binary_encoder("<d"),
    datetime64: lambda v, l: trim_or_pad_bytes(
        format_datetime64(v).encode("ascii"), l
    )
}


BINARY_ITEM_SIZE = {
    str_: lambda t: t.itemsize,
    bytes_: lambda t: t.itemsize,
    bool_: lambda _: 1,
    int8: lambda _: 1,
    int16: lambda _: 2,
    int32: lambda _: 4,
    int64: lambda _: 8,
    uint8: lambda _: 1,
    uint16: lambda _: 2,
    uint32: lambda _: 4,
    uint64: lambda _: 8,
    float32: lambda _: 4,
    float64: lambda _: 8,
    datetime64: get_datetime64_string_size,
}


# casting types required by the HAPI specification
HAPI_TYPE_MAPPING = {
    bool_: int32,
    int8: int32,
    int16: int32,
    uint8: int32,
    uint16: int32,
    float32: float64
}

# types which can be safely stored by the HAPI binary format
HAPI_UNSUPPORTED_TYPES = {int64, uint32, uint64, }


def get_hapi_type(type_):
    """ Get the type data type required to store the given type. """
    if type_ in HAPI_UNSUPPORTED_TYPES:
        raise TypeError(
            f"{type_} array cannot be safely stored by the HAPI binary format!."
        )
    return HAPI_TYPE_MAPPING.get(type_) or type_


def cast_array_to_allowed_hapi_types(arrays):
    """ Cast array types to the required HAPI binary data types. """
    # cast arrays to the required types
    return [
        array if array.dtype.type == type_ else array.astype(type_)
        for array, type_ in (
            (array, get_hapi_type(array.dtype.type)) for array in arrays
        )
    ]


def arrays_to_binary(file, arrays, encoders=None, item_sizes=None):
    """ Convert Numpy arrays into binary records written in the output file."""
    type_encoding = {**BINARY_ENCODING, **(encoders or {})}
    type_item_size = {**BINARY_ITEM_SIZE, **(item_sizes or {})}
    field_encoding = [
        (type_encoding[dt.type], type_item_size[dt.type](dt))
        for dt in (array.dtype for array in arrays)
    ]
    arrays = [flatten_records(array) for array in arrays]
    for record in zip(*arrays):
        file.write(b"".join(chain.from_iterable(
            (format_(item, size) for item in field)
            for field, (format_, size) in zip(record, field_encoding)
        )))
