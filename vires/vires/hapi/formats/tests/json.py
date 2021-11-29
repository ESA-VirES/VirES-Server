#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - JSON format subroutines - test
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
# pylint: disable=missing-docstring,no-self-use,too-many-public-methods

import json
from unittest import TestCase, main
from io import StringIO
from numpy import array
from numpy.testing import assert_equal
from vires.hapi.formats.json import (
    arrays_to_json_fragment,
    arrays_to_plain_records,
)
from .base import FormatTestMixIn


class TestArraysToJsonFragment(FormatTestMixIn, TestCase):

    def _test(self, *arrays, dump=False):
        array_types = [(a.dtype, a.shape[1:]) for a in arrays]
        buffer_ = arrays_to_json_fragment(arrays)
        if dump:
            print(buffer_)
        parsed_arrays = _parse_json_fragment(buffer_, array_types)
        for source, parsed in zip(arrays, parsed_arrays):
            assert_equal(source, parsed)


class TestArraysToPlainRecords(FormatTestMixIn, TestCase):

    def _test(self, *arrays, dump=False):
        array_types = [(a.dtype, a.shape[1:]) for a in arrays]
        records = arrays_to_plain_records(arrays)
        if dump:
            print(records)
        parsed_arrays = _parse_plain_records(records, array_types)
        for source, parsed in zip(arrays, parsed_arrays):
            assert_equal(source, parsed)


def _parse_json_fragment(buffer_, types):

    # turn fragment into a proper JSON object
    if buffer_ and buffer_[-1:] == b",":
        buffer_ = buffer_[:-1]
    buffer_ = b"".join([b"[", buffer_, b"]"])

    parsed_records = json.loads(buffer_.decode('ascii'))
    return _parse_plain_records(parsed_records, types)


def _parse_plain_records(records, types):

    def _records_to_lists(records):

        try:
            record = next(records)
            lists = tuple([item] for item in record)
        except StopIteration:
            pass

        for record in records:
            for list_, item in zip(lists, record):
                list_.append(item)

        return tuple(
            array(list_, dtype=type_).reshape((len(list_), *shape))
            for list_, (type_, shape) in zip(lists, types)
        )

    return _records_to_lists(iter(records))


if __name__ == "__main__":
    main()
