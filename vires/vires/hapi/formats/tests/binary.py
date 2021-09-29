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
from io import BytesIO
from numpy import (
    array, prod,
    str_, bytes_, bool_, float32, float64, datetime64,
    uint8, uint16, uint32, uint64, int8, int16, int32, int64,
)
from numpy.testing import assert_equal
from vires.hapi.formats.binary import (
    arrays_to_binary, BINARY_ITEM_SIZE,
    cast_array_to_allowed_hapi_types,
    get_hapi_type,
)
from .base import FormatTestMixIn, random_integer_array


class TestArraysToBinary(FormatTestMixIn, TestCase):

    def _test(self, *arrays, dump=False):
        array_types = [(a.dtype, a.shape[1:]) for a in arrays]
        buffer_ = BytesIO()
        arrays_to_binary(buffer_, arrays)
        if dump:
            buffer_.seek(0)
            print(buffer_.read())
        buffer_.seek(0)
        parsed_arrays = _parse_binary(buffer_, array_types)
        for source, parsed in zip(arrays, parsed_arrays):
            assert_equal(source, parsed)


class TestArraysToHapiBinary(TestArraysToBinary):

    def _test(self, *arrays, dump=False):
        output_arrays = cast_array_to_allowed_hapi_types(arrays)
        super()._test(*output_arrays, dump=dump)
        for input_, output in zip(arrays, output_arrays):
            assert_equal(input_, output)
            assert_equal(get_hapi_type(input_.dtype.type), output.dtype.type)

    def _test_failed(self, *arrays):
        with self.assertRaises(TypeError):
            cast_array_to_allowed_hapi_types(arrays)

    def test_int64_array_0d(self):
        self._test_failed(random_integer_array((20,), 'int64'))

    def test_uint32_array_0d(self):
        self._test_failed(random_integer_array((20,), 'uint32'))

    def test_uint64_array_0d(self):
        self._test_failed(random_integer_array((20,), 'uint64'))



class TestHapiBinaryTypeMapping(TestCase):

    def _test_hapi_type_mapping_supported(self, type_, expected=None):
        self.assertEqual(get_hapi_type(type_), expected or type_)

    def _test_hapi_type_mapping_unsupported(self, type_):
        with self.assertRaises(TypeError):
            get_hapi_type(type_)

    def test_hapi_type_mapping_str(self):
        self._test_hapi_type_mapping_supported(str_)

    def test_hapi_type_mapping_bytes(self):
        self._test_hapi_type_mapping_supported(bytes_)

    def test_hapi_type_mapping_bool(self):
        self._test_hapi_type_mapping_supported(bool_, int32)

    def test_hapi_type_mapping_int8(self):
        self._test_hapi_type_mapping_supported(int8, int32)

    def test_hapi_type_mapping_int16(self):
        self._test_hapi_type_mapping_supported(int16, int32)

    def test_hapi_type_mapping_int32(self):
        self._test_hapi_type_mapping_supported(int32)

    def test_hapi_type_mapping_int64(self):
        self._test_hapi_type_mapping_unsupported(int64)

    def test_hapi_type_mapping_uint8(self):
        self._test_hapi_type_mapping_supported(uint8, int32)

    def test_hapi_type_mapping_uint16(self):
        self._test_hapi_type_mapping_supported(uint16, int32)

    def test_hapi_type_mapping_uint32(self):
        self._test_hapi_type_mapping_unsupported(uint32)

    def test_hapi_type_mapping_uint64(self):
        self._test_hapi_type_mapping_unsupported(uint64)

    def test_hapi_type_mapping_float32(self):
        self._test_hapi_type_mapping_supported(float32, float64)

    def test_hapi_type_mapping_float64(self):
        self._test_hapi_type_mapping_supported(float64)

    def test_hapi_type_mapping_datetime64(self):
        self._test_hapi_type_mapping_supported(datetime64)


def _binary_decoder(format_):
    """ Build binary value encoder. """
    def _decoder(buffer_):
        return unpack(format_, buffer_)
    return _decoder

BINARY_DECODERS = {
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
    datetime64: lambda v: v.rstrip(b"\x00").decode('ascii'),
}


def _parse_binary(file, types):
    """ CSV output parser. """

    def _read_records():

        fields = [
            (
                BINARY_DECODERS[type_.type],
                BINARY_ITEM_SIZE[type_.type](type_),
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
            record = file.read(record_size)
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

    return _records_to_lists(_read_records())


if __name__ == "__main__":
    main()
