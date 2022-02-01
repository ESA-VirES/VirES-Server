#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - JSON format subroutines
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


import json
from itertools import chain
from numpy import (
    str_, bytes_, bool_, float32, float64, datetime64,
    int8, int16, int32, int64, uint8, uint16, uint32, uint64,
    isfinite, char,
)
from .common import (
    flatten_records, format_datetime64_array,
    convert_arrays,
)


JSON_ARRAY_CONVERSIONS = {
    datetime64: lambda a: char.decode(format_datetime64_array(a), 'ASCII'),
    bytes_: lambda a: char.decode(a, 'UTF-8'),
}


def arrays_to_json_fragment(arrays, encoding='ascii', newline="\r\n"):
    """ Convert Numpy arrays into bytes array holding the JSON-encoded records."""

    def _encode_records(arrays, newline):
        for record in arrays_to_plain_records(arrays):
            yield newline
            yield json.dumps(record).encode(encoding)
            yield b","

    return b"".join(_encode_records(
        convert_arrays(arrays, JSON_ARRAY_CONVERSIONS),
        newline.encode(encoding),
    ))


def arrays_to_plain_records(arrays):
    """ Convert Numpy arrays into JSON serializable records."""
    scalar_flags = [not array.shape[1:] for array in arrays]
    arrays = [flatten_records(array) for array in arrays]

    for record in zip(*arrays):
        yield [
            (field[0] if is_scalar else field).tolist()
            for field, is_scalar in zip(record, scalar_flags)
        ]
