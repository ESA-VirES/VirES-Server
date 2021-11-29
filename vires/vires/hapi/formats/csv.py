#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - CSV format subroutines
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
from io import BytesIO, TextIOWrapper, StringIO
from numpy import str_, bytes_, bool_, float32, float64, datetime64
from .common import flatten_records, format_datetime64


def quote_csv_string(value, delimiter=",", quote='"', escaped_quote='""', new_line="\n"):
    """ CSV string quoting. """
    string_needs_quotes = (
        delimiter in value or quote in value or new_line in value
    )
    if string_needs_quotes:
        value = "%s%s%s" % (quote, value.replace(quote, escaped_quote), quote)
    return value


DEFAULT_TEXT_FORMATTING = str # pylint: disable=invalid-name
TEXT_FORMATTING = {
    str_: quote_csv_string,
    bytes_: lambda v, **kwargs: quote_csv_string(bytes(v).decode('ascii'), **kwargs),
    bool_: lambda v: str(int(v)),
    float32: lambda v: "%.9g" % v,
    float64: lambda v: "%.17g" % v,
    datetime64: format_datetime64,
}


def arrays_to_csv(arrays, delimiter=",", newline="\r\n", encoding="UTF-8"):
    """ Convert Numpy arrays into a CSV byte-string. """
    return _lines_to_bytes(
        lines=_arrays_to_csv_lines(
            arrays=arrays,
            delimiter=delimiter
        ),
        newline=newline.encode(encoding),
        encoding=encoding,
    )


def _lines_to_bytes(lines, newline, encoding):
    return newline.join(line.encode(encoding) for line in lines)


def _arrays_to_csv_lines(arrays, delimiter=","):
    field_formatting = [
        TEXT_FORMATTING.get(array.dtype.type) or DEFAULT_TEXT_FORMATTING
        for array in arrays
    ]
    arrays = [flatten_records(array) for array in arrays]
    for record in zip(*arrays):
        yield from delimiter.join(chain.from_iterable(
            (format_(item) for item in field)
            for field, format_ in zip(record, field_formatting)
        )).split("\n")
    yield ""
