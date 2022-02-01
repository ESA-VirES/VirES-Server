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

import csv
from itertools import chain
from io import BytesIO, TextIOWrapper
from numpy import bytes_, bool_, datetime64, char
from .common import flatten_records, convert_arrays, format_datetime64_array


CSV_ARRAY_CONVERSIONS = {
    datetime64: lambda a: char.decode(format_datetime64_array(a), 'ASCII'),
    bytes_: lambda a: char.decode(a, 'UTF-8'),
    bool_: lambda a: a.astype('uint8'),
}


class HapiCsvDialect(csv.Dialect):
    """ HAPI CSV dialect specification. """
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL


def arrays_to_csv(arrays):
    """ Convert Numpy arrays into a CSV byte-string. """
    arrays = map(flatten_records, convert_arrays(arrays, CSV_ARRAY_CONVERSIONS))

    buffer_ = BytesIO()
    text_buffer = TextIOWrapper(buffer_, encoding="UTF-8", write_through=True)

    writer = csv.writer(text_buffer, HapiCsvDialect)
    for record in zip(*arrays):
        writer.writerow(
            tuple(chain.from_iterable(
                item.tolist() for item in record
            ))
        )

    return buffer_.getvalue()
