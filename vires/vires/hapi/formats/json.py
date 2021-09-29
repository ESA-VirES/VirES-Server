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
from numpy import (
    str_, bytes_, bool_, float32, float64, datetime64,
    int8, int16, int32, int64, uint8, uint16, uint32, uint64,
)
from .common import flatten_records, format_datetime64

DEFAULT_JSON_FORMATTING = lambda v: v # simple pass-trough
JSON_FORMATTING = {
    str_: str,
    bytes_: lambda v: bytes(v).decode('ascii'),
    bool_: int,
    int8: int,
    int16: int,
    int32: int,
    int64: int,
    uint8: int,
    uint16: int,
    uint32: int,
    uint64: int,
    float32: float,
    float64: float,
    datetime64: format_datetime64,
}


def arrays_to_json_fragment(file, arrays, prefix="\n", suffix=",", formats=None):
    """ Convert Numpy arrays into JSON fragment holding the records."""
    for record in arrays_to_plain_records(arrays, formats=formats):
        file.write(prefix)
        file.write(json.dumps(record))
        file.write(suffix)


def arrays_to_plain_records(arrays, formats=None):
    """ Convert Numpy arrays into JSON serializable records."""
    type_formatting = {**JSON_FORMATTING, **(formats or {})}
    field_formatting = [
        type_formatting.get(array.dtype.type) or DEFAULT_JSON_FORMATTING
        for array in arrays
    ]

    scalar_flags = [not array.shape[1:] for array in arrays]
    arrays = [flatten_records(array) for array in arrays]

    for record in zip(*arrays):
        yield [
            item[0] if is_scalar else item
            for item, is_scalar in zip((
                [format_(item) for item in field]
                for field, format_ in zip(record, field_formatting)
            ), scalar_flags)
        ]
