#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - CSV format subroutines - test
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
from io import BytesIO, TextIOWrapper
from numpy import array, prod, cumsum, bool_
from numpy.testing import assert_equal
from vires.hapi.formats.csv import quote_csv_string, arrays_to_csv
from .base import FormatTestMixIn


class TestCsvStringQuotation(TestCase):

    def _test_quote_csv_string(self, input_, expected_output):
        self.assertEqual(quote_csv_string(input_), expected_output)

    def test_no_quote(self):
        self._test_quote_csv_string('ABCD', 'ABCD')

    def test_with_quote(self):
        self._test_quote_csv_string('"ABCD"', '"""ABCD"""')
        self._test_quote_csv_string('ABCD"', '"ABCD"""')
        self._test_quote_csv_string('"ABCD', '"""ABCD"')
        self._test_quote_csv_string('AB"CD', '"AB""CD"')

    def test_with_field_delimiter(self):
        self._test_quote_csv_string('AB,CD', '"AB,CD"')

    def test_with_record_delimiter(self):
        self._test_quote_csv_string('AB\nCD', '"AB\nCD"')


class TestArraysToCsv(FormatTestMixIn, TestCase):

    def _test(self, *arrays, dump=False):
        array_types = [(a.dtype, a.shape[1:]) for a in arrays]
        buffer_ = arrays_to_csv(arrays)
        if dump:
            print(buffer_)
        parsed_arrays = _parse_csv(buffer_, array_types)
        for source, parsed in zip(arrays, parsed_arrays):
            assert_equal(source, parsed)


TEXT_DECODERS = {
    bool_: lambda v, dt: array(v, dtype='uint8').astype(dt),
}
TEXT_DEFAULT_DECODER = lambda v, dt: array(v, dtype=dt)


def _parse_csv(data, types, field_delimiter=",", record_delimiter="\n", quote="\""):
    """ CSV output parser. """
    # pylint: disable=too-many-branches,too-many-statements

    def _tokenize(file):
        buffer_ = []
        is_quoted = False
        while True:
            char = file.read(1)
            if not char: # EoF
                if is_quoted:
                    raise ValueError("Unterminated quoted string!")
                if buffer_:
                    raise ValueError("Unteminated record!")
                break

            if is_quoted:
                if char == quote:
                    char = file.read(1)
                    if char == quote:
                        buffer_.append(char)
                        continue
                    if char not in (field_delimiter, record_delimiter):
                        raise ValueError("Misplaced end of string quotation!")
                    is_quoted = False
                else:
                    buffer_.append(char)
                    continue

            if char in (field_delimiter, record_delimiter):
                yield (True, "".join(buffer_))
                yield (False, char)
                buffer_ = []

            elif char == quote:
                if buffer_:
                    raise ValueError("Misplaced start of string quotation!")
                is_quoted = True
            else:
                buffer_.append(char)

    def _group_records(tokens):
        record, expect_field = [], True

        for is_field, token in tokens:
            if is_field:
                if not expect_field:
                    raise ValueError("Missing field delimiter!")
                record.append(token)
                expect_field = False

            else:
                if expect_field:
                    raise ValueError("Missing field content!")
                if token == record_delimiter:
                    yield tuple(record)
                    record = []
                expect_field = True

        if record:
            raise ValueError("Incomplete trailing record!")

    def _records_to_lists(records, offsets):

        def _aggregate_fields(record):
            return tuple(
                record[start:end]
                for start, end in zip(offsets[:-1], offsets[1:])
            )

        record_length = None
        lists = None

        try:
            record = next(records)
            record_length = len(record)
            lists = tuple([item] for item in _aggregate_fields(record))
        except StopIteration:
            pass

        for record in records:
            if len(record) != record_length:
                raise ValueError("Record size mismatch!")

            for list_, item in zip(lists, _aggregate_fields(record)):
                list_.append(item)

        return tuple(
            (
                TEXT_DECODERS.get(type_.type) or TEXT_DEFAULT_DECODER
            )(list_, type_).reshape((len(list_), *shape))
            for list_, (type_, shape) in zip(lists, types)
        )

    field_counts = cumsum([0, *(prod(shape or (1,)) for _, shape in types)])

    return _records_to_lists(_group_records(_tokenize(
        TextIOWrapper(BytesIO(data), encoding="UTF-8")
    )), field_counts)


if __name__ == "__main__":
    main()
