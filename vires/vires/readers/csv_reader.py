#-------------------------------------------------------------------------------
#
# VirES CSV format reader
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
from numpy import array, datetime64
from .exceptions import InvalidFileFormat


def read_csv_data(path):
    """ Read data from a VirES compatible CSV file and get a dictionary
    of arrays.
    """
    try:
        with open(path, "rb") as file_:
            data = records_to_list(parse_record_values(read_csv_file(file_)))
    except csv.Error as error:
        raise InvalidFileFormat(str(error))

    return lists_to_arrays(data)


def lists_to_arrays(data):
    """ Convert a dictionary list to a dictionary of NumPy arrays. """
    return {field: array(values) for field, values in data.items()}


def read_csv_file(file_):
    """ Generator parsing VirES CSV from a file yielding raw parsed records.
    """
    records = csv.reader(file_)
    header = next(records)
    yield header
    for line_no, record in enumerate(records, 2):
        if len(record) != len(header):
            raise csv.Error(
                "CSV file: line %d: record length mismatch! %d != %d"
                % (line_no, len(record), len(header))
            )
        yield record


def parse_record_values(records):
    """ Parse the raw string records values. """
    type_parsers = [int, float, parse_csv_array, parse_datetime]

    def _parse_value(value, type_parser):
        try:
            return type_parser(value), type_parser
        except (ValueError, TypeError):
            pass

        for type_parser_ in type_parsers:
            try:
                return type_parser_(value), type_parser
            except (ValueError, TypeError):
                continue
        # no type matched passing trough the original string
        return value, str

    header = next(records)
    yield header

    parsers = [type_parsers[0]] * len(header)
    for record in records:
        temp = [
            _parse_value(value, parser)
            for parser, value in zip(parsers, record)
        ]
        parsers = [parser for _, parser in temp]
        yield [value for value, _ in temp]


def records_to_list(records):
    """ Convert a sequence of records to dictionary or lists. """
    header = next(records)
    data = [[] for _ in header]
    for record in records:
        for value, list_ in zip(record, data):
            list_.append(value)
    return {field: list_ for field, list_ in zip(header, data)}


def parse_datetime(value):
    """ Parse ISO-8601 time-stamp to NumPy datetime64 with a milliseconds
    resolution.
    """
    return datetime64(value, 'ms')


def parse_csv_array(value, start="{", end="}", delimiter=";"):
    """ Parse CSV array values """

    def _parse_array(string):
        data = []
        while True:
            idx = string.find(delimiter)
            if idx == -1:
                idx = string.find(end)
                if idx == -1:
                    raise ValueError("Missing closing brace!")
                tmp = string[:idx]
                if tmp:
                    data.append(float(tmp))
                break
            elif idx > 1 and string[idx-1] == end:
                tmp = string[:idx-1]
                if tmp:
                    data.append(float(tmp))
                break
            if string[0] == start:
                string, tmp = _parse_array(string[1:])
                data.append(tmp)
            else:
                data.append(float(string[:idx]))
                string = string[idx+1:]
        return string[idx+1:], data

    # remove white-spaces
    value = "".join(value.split())

    if not value or value[0] != start:
        raise ValueError("Missing opening brace!")

    _, data = _parse_array(value[1:])
    return data
