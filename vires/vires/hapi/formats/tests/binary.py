#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - binary format subroutines - test
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

from unittest import TestCase, main
from struct import unpack
from numpy import (
    array, prod,
    str_, bytes_, bool_, float32, float64, datetime64,
    uint8, uint16, uint32, uint64, int8, int16, int32, int64,
)
from numpy.testing import assert_equal
from vires.hapi.formats.binary import (
    arrays_to_hapi_binary, arrays_to_x_binary,
)
from vires.hapi.formats.common import (
    get_datetime64_string_size,
)
from .base import (
    FormatTestMixIn, random_integer_array, random_nonnegative_integer_array,
)

def constant_item_size(size):
    """ Build function for a constant item size. """
    def _item_size(_):
        return size
    return _item_size


HAPI_BINARY_TYPE_MAPPING = {
    bool_: int32,
    int8: int32,
    int16: int32,
    uint8: int32,
    uint16: int32,
    float32: float64,
}


HAPI_BINARY_ITEM_SIZE = {
    str_: lambda t: t.itemsize,
    bytes_: lambda t: t.itemsize,
    int32: constant_item_size(4),
    int64: constant_item_size(4),
    uint32: constant_item_size(4),
    uint64: constant_item_size(4),
    float64: constant_item_size(8),
    datetime64: get_datetime64_string_size,
}


X_BINARY_TYPE_MAPPING = {
    datetime64: int64,
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


def _binary_decoder(format_):
    """ Build binary value encoder. """
    def _decoder(buffer_):
        return unpack(format_, buffer_)
    return _decoder


class BinaryFormatTestMixIn(FormatTestMixIn):
    TYPE_MAPPING = None
    ITES_SIZES = None
    DECODERS = None

    @staticmethod
    def _arrays_to_binary(arrays):
        raise NotImplementedError

    def _test(self, *arrays, dump=False):
        array_types = [(a.dtype, a.shape[1:]) for a in arrays]
        buffer_ = self._arrays_to_binary(arrays)
        if dump:
            print(buffer_)
        parsed_arrays = _parse_binary(
            buffer_, array_types,
            self.DECODERS, self.ITES_SIZES, self.TYPE_MAPPING,
        )
        for source, parsed in zip(arrays, parsed_arrays):
            assert_equal(source, parsed)
            assert_equal(source.dtype.type, parsed.dtype.type)


class TestArraysToXBinary(BinaryFormatTestMixIn, TestCase):
    TYPE_MAPPING = X_BINARY_TYPE_MAPPING
    ITES_SIZES = X_BINARY_ITEM_SIZE
    DECODERS = {
        str_: lambda v: v.rstrip(b"\x00").decode('utf8'),
        bytes_: lambda v: v.rstrip(b"\x00"),
        bool_: _binary_decoder("?"),
        int8: _binary_decoder("b"),
        int16: _binary_decoder("<h"),
        int32: _binary_decoder("<l"),
        int64: _binary_decoder("<q"),
        uint8: _binary_decoder("B"),
        uint16: _binary_decoder("<H"),
        uint32: _binary_decoder("<L"),
        uint64: _binary_decoder("<Q"),
        float32: _binary_decoder("<f"),
        float64: _binary_decoder("<d"),
        datetime64: _binary_decoder("<Q"),
    }

    @staticmethod
    def _arrays_to_binary(arrays):
        return arrays_to_x_binary(arrays)


class TestArraysToHapiBinary(BinaryFormatTestMixIn, TestCase):
    TYPE_MAPPING = HAPI_BINARY_TYPE_MAPPING
    ITES_SIZES = HAPI_BINARY_ITEM_SIZE
    DECODERS = HAPI_BINARY_DECODERS = {
        str_: lambda v: v.rstrip(b"\x00").decode('utf8'),
        bytes_: lambda v: v.rstrip(b"\x00"),
        int32: _binary_decoder("<l"),
        int64: _binary_decoder("<l"),
        uint32: _binary_decoder("<l"),
        uint64: _binary_decoder("<l"),
        float64: _binary_decoder("<d"),
        datetime64: lambda v: v.rstrip(b"\x00").decode('ascii'),
    }

    @staticmethod
    def _arrays_to_binary(arrays):
        return arrays_to_hapi_binary(arrays)

    def _test_failed(self, *arrays):
        with self.assertRaises(TypeError):
            arrays_to_hapi_binary(arrays)

    def test_int64_array_0d(self):
        self._test(random_integer_array((20,), 'int32').astype('int64'))

    def test_uint32_array_0d(self):
        self._test(random_nonnegative_integer_array((20,), 'int32').astype('uint32'))

    def test_uint64_array_0d(self):
        self._test(random_nonnegative_integer_array((20,), 'int32').astype('uint64'))


def _parse_binary(data, types, decoders, item_sizes, type_mapping):
    """ CSV output parser. """

    def _read_records(data):

        def _map_type(type_):
            return type_mapping.get(type_, type_)

        fields = [
            (
                decoders[_map_type(type_.type)],
                item_sizes[_map_type(type_.type)](type_),
                int(prod(shape or (1,)))
            ) for type_, shape in types
        ]

        record_size = sum(size * count for _, size, count in fields)

        def _decode_record(record):

            def _decode_field(field, decode, item_size, item_count):
                for _ in range(item_count):
                    item, field = field[:item_size], field[item_size:]
                    yield decode(item)

            for decode, item_size, item_count in fields:
                field_size = item_size * item_count
                field, record = record[:field_size], record[field_size:]
                yield tuple(_decode_field(field, decode, item_size, item_count))

        while True:
            record, data = data[:record_size], data[record_size:]
            if not record:
                break
            if len(record) != record_size:
                raise ValueError("Incomplete record!")

            yield tuple(_decode_record(record))

    def _records_to_lists(records):

        lists = None

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

    return _records_to_lists(_read_records(data))


if __name__ == "__main__":
    main()
