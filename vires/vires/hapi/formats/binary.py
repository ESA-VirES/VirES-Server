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
    str_, bytes_, bool_, float32, float64, datetime64,
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


def constant_item_size(size):
    """ Build function for a constant item size. """
    def _item_size(_):
        return size
    return _item_size


def trim_or_pad_bytes(byte_string, lenght):
    """ Trim or pad bytes to the requested byte length. """
    return byte_string[:lenght].ljust(lenght, b'\x00')


# standard HAPI binary encoding

HAPI_BINARY_ENCODING = {
    str_: lambda v, l: trim_or_pad_bytes(v.encode("utf8"), l),
    bytes_: trim_or_pad_bytes,
    int32: binary_encoder("<l"),
    float64: binary_encoder("<d"),
    datetime64: lambda v, l: trim_or_pad_bytes(
        format_datetime64(v).encode("ascii"), l
    ),
}

HAPI_BINARY_ITEM_SIZE = {
    str_: lambda t: t.itemsize,
    bytes_: lambda t: t.itemsize,
    int32: constant_item_size(4),
    float64: constant_item_size(8),
    datetime64: get_datetime64_string_size,
}

HAPI_BINARY_TYPE_MAPPING = {
    bool_: int32,
    int8: int32,
    int16: int32,
    uint8: int32,
    uint16: int32,
    float32: float64,
}

HAPI_BINARY_UNSUPPORTED_TYPES = {int64, uint32, uint64}


def arrays_to_hapi_binary(arrays):
    """ Serialize Numpy arrays into byte-string in the HAPI binary format. """

    for array in arrays:
        type_ = array.dtype.type
        if type_ in HAPI_BINARY_UNSUPPORTED_TYPES:
            raise TypeError(
                f"{type_} array cannot be safely stored by the HAPI binary "
                "format!."
            )

    return b"".join(_arrays_to_binary_records(
        arrays=_cast_arrays(arrays, HAPI_BINARY_TYPE_MAPPING),
        type_encoding=HAPI_BINARY_ENCODING,
        type_item_size=HAPI_BINARY_ITEM_SIZE,
    ))


# extended HAPI binary encoding

X_BINARY_ENCODING = {
    **HAPI_BINARY_ENCODING,
    bool_: binary_encoder("?"),
    int8: binary_encoder("b"),
    int16: binary_encoder("<h"),
    int64: binary_encoder("<q"),
    uint8: binary_encoder("B"),
    uint16: binary_encoder("<H"),
    uint32: binary_encoder("<L"),
    uint64: binary_encoder("<Q"),
    float32: binary_encoder("<f"),
}

X_BINARY_ITEM_SIZE = {
    **HAPI_BINARY_ITEM_SIZE,
    bool_: constant_item_size(1),
    int8: constant_item_size(1),
    int16: constant_item_size(2),
    int64: constant_item_size(8),
    uint8: constant_item_size(1),
    uint16: constant_item_size(2),
    uint32: constant_item_size(4),
    uint64: constant_item_size(8),
    float32: constant_item_size(4),
}

X_BINARY_TYPE_MAPPING = {
    datetime64: int64,
}


def arrays_to_x_binary(arrays):
    """ Serialize Numpy arrays into byte-string in the custom binary format. """
    return b"".join(_arrays_to_binary_records(
        arrays=_cast_arrays(arrays, type_mapping=X_BINARY_TYPE_MAPPING),
        type_encoding=X_BINARY_ENCODING,
        type_item_size=X_BINARY_ITEM_SIZE,
    ))


def _arrays_to_binary_records(arrays, type_encoding, type_item_size):
    """ Generate binary records. """
    field_encoding = [
        (type_encoding[dt.type], type_item_size[dt.type](dt))
        for dt in (array.dtype for array in arrays)
    ]
    arrays = [flatten_records(array) for array in arrays]
    for record in zip(*arrays):
        yield b"".join(chain.from_iterable(
            (format_(item, size) for item in field)
            for field, (format_, size) in zip(record, field_encoding)
        ))


def _cast_arrays(arrays, type_mapping):
    """ Cast arrays to the desired type. """

    def _get_type(type_):
        return type_mapping.get(type_, type_)

    return [
        array if array.dtype.type == type_ else array.astype(type_)
        for array, type_ in (
            (array, _get_type(array.dtype.type)) for array in arrays
        )
    ]
