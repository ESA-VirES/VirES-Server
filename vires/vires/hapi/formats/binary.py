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

from sys import byteorder as system_byteorder
from numpy import (
    dtype, empty, full, choose, isnat,
    str_, bytes_, bool_, float32, float64, datetime64,
    uint8, uint16, uint32, uint64, int8, int16, int32, int64,
)
from .common import (
    format_datetime64_array, get_datetime64_string_size,
    encode_string_array, convert_arrays,
)


def _astype_conversion(type_):
    """ Get as-type array conversion. """
    def _convert_astype(array):
        return array.astype(type_)
    return _convert_astype


HAPI_BYTEORDER = 'little'

HAPI_BINARY_TYPE_MAPPING = {
    bool_: int32,
    int8: int32,
    int16: int32,
    #int32: int32,
    int64: int32, # may overflow!
    uint8: int32,
    uint16: int32,
    uint32: int32, # may overflow!
    uint64: int32, # may overflow!
    float32: float64,
}

HAPI_BINARY_UNSUPPORTED_TYPES = {}

HAPI_ARRAY_CONVERSIONS = {
    datetime64: format_datetime64_array,
    str_: encode_string_array,
    **{
        src_type: _astype_conversion(dst_type)
        for src_type, dst_type in HAPI_BINARY_TYPE_MAPPING.items()
    }
}

X_ARRAY_CONVERSIONS = {
    str_: encode_string_array,
}


def arrays_to_hapi_binary(arrays):
    """ Serialize Numpy arrays into byte-string in the HAPI binary format. """

    for array in arrays:
        type_ = array.dtype.type
        if type_ in HAPI_BINARY_UNSUPPORTED_TYPES:
            raise TypeError(
                f"{type_} array cannot be safely stored by the HAPI binary "
                "format!."
            )

    return _arrays_to_binary(convert_arrays(arrays, HAPI_ARRAY_CONVERSIONS))


def arrays_to_x_binary(arrays):
    """ Serialize Numpy arrays into byte-string in the custom binary format. """
    return _arrays_to_binary(convert_arrays(arrays, X_ARRAY_CONVERSIONS))


def _arrays_to_binary(arrays):
    """ Serialize Numpy arrays into byte-string. """
    return _assure_byteorder(
        _convert_arrays_to_struct_array(arrays),
        byteorder=HAPI_BYTEORDER, inplace=True,
    ).tobytes(order='C')

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


def _assure_byteorder(array, byteorder, inplace=False):
    """ Convert array byte order or the desired 'little' (default) or 'big'
    endian byte order.
    """
    if system_byteorder != byteorder:
        array = array.newbyteorder().byteswap(inplace=inplace)
    return array


def _convert_arrays_to_struct_array(arrays):
    """ Convert a list of arrays to a structured array. """
    arrays = list(arrays)
    size = arrays[0].shape[0] if arrays else 0
    labels = [f"f{idx}" for idx in range(len(arrays))]

    struct_dtype = dtype([
        (label, array.dtype, array.shape[1:])
        for label, array in zip(labels, arrays)
    ])

    data = empty(size, struct_dtype)
    for label, array in zip(labels, arrays):
        data[label] = array

    return data
