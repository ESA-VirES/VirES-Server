#-------------------------------------------------------------------------------
#
#  Data filters - single variable predicates - tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2022 EOX IT Services GmbH
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
# pylint: disable=missing-docstring

from unittest import TestCase, main
from numpy import nan, inf, array
from numpy.random import randint
from vires.dataset import Dataset
from vires.filters import (
    FilterError,
    EqualFilter,
    NotEqualFilter,
    StringEqualFilter,
    StringNotEqualFilter,
    BitmaskEqualFilter,
    BitmaskNotEqualFilter,
    LessThanFilter,
    GreaterThanFilter,
    LessThanOrEqualFilter,
    GreaterThanOrEqualFilter,
    IsNanFilter,
    IsNotNanFilter,
)
from vires.filters.tests.common import FilterTestMixIn


class TestIndexing(TestCase):
    # Note that the data indexing is shared by all filters and thus it does not
    # need to be tested with all of them.

    def build_dataset(self, **data):
        dataset = Dataset()
        for variable, data in data.items():
            dataset.set(variable, array(data))
        return dataset

    def test_scalar_filter_on_array_data(self):
        data = self.build_dataset(x=randint(2, size=(10, 2, 3)))
        filter_ = EqualFilter(("x", None), 1)
        with self.assertRaises(FilterError):
            filter_.filter(data)

    def test_array_filter_on_scalar_data(self):
        data = self.build_dataset(x=randint(2, size=(10,)))
        filter_ = EqualFilter(("x", (0,)), 1)
        with self.assertRaises(FilterError):
            filter_.filter(data)

    def test_dimension_mismatch_too_few_dimensions(self):
        data = self.build_dataset(x=randint(2, size=(10, 2, 3)))
        filter_ = EqualFilter(("x", (1,)), 1)
        with self.assertRaises(FilterError):
            filter_.filter(data)

    def test_dimension_mismatch_too_many_dimensions(self):
        data = self.build_dataset(x=randint(2, size=(10, 2, 3)))
        filter_ = EqualFilter(("x", (1, 2, 3)), 1)
        with self.assertRaises(FilterError):
            filter_.filter(data)

    def test_index_exceeds_array_size(self):
        data = self.build_dataset(x=randint(2, size=(10, 2, 3)))
        filter_ = EqualFilter(("x", (1, 3)), 1)
        with self.assertRaises(FilterError):
            filter_.filter(data)

# -----------------------------------------------------------------------------

class BoolTestMixIn:
    REQUIRED_VARIABLES = ("B",)
    DATA = {"B": [True, False, True, False]}


class TestEqualFilterBoolTrue(TestCase, BoolTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("B", True)
    STRING = "B == True"
    RESULT = [0, 2]


class TestEqualFilterBoolFalse(TestCase, BoolTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("B", False)
    STRING = "B == False"
    RESULT = [1, 3]


class TestNotEqualFilterBoolTrue(TestCase, BoolTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("B", True)
    STRING = "B != True"
    RESULT = [1, 3]


class TestNotEqualFilterBoolFalse(TestCase, BoolTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("B", False)
    STRING = "B != False"
    RESULT = [0, 2]

# -----------------------------------------------------------------------------

class IntTestMixIn:
    REQUIRED_VARIABLES = ("I",)
    DATA = {"I": [4, -1, 1, 2, 5, 0, 3]}


class TestEqualFilterInt(TestCase, IntTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("I", 2)
    STRING = "I == 2"
    RESULT = [3]


class TestNotEqualFilterInt(TestCase, IntTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("I", 2)
    STRING = "I != 2"
    RESULT = [0, 1, 2, 4, 5, 6]


class TestLessThanFilterInt(TestCase, IntTestMixIn, FilterTestMixIn):
    CLASS = LessThanFilter
    ARGS = ("I", 2)
    STRING = "I < 2"
    RESULT = [1, 2, 5]


class TestGreaterThanFilterInt(TestCase, IntTestMixIn, FilterTestMixIn):
    CLASS = GreaterThanFilter
    ARGS = ("I", 2)
    STRING = "I > 2"
    RESULT = [0, 4, 6]


class TestLessThanOrEqualFilterInt(TestCase, IntTestMixIn, FilterTestMixIn):
    CLASS = LessThanOrEqualFilter
    ARGS = ("I", 2)
    STRING = "I <= 2"
    RESULT = [1, 2, 3, 5]


class TestGreaterThanOrEqualFilterInt(TestCase, IntTestMixIn, FilterTestMixIn):
    CLASS = GreaterThanOrEqualFilter
    ARGS = ("I", 2)
    STRING = "I >= 2"
    RESULT = [0, 3, 4, 6]

# -----------------------------------------------------------------------------

class FloatTestMixIn:
    REQUIRED_VARIABLES = ("F",)
    DATA = {"F": [400.0, -1e-3, 0.1, 2.0, 5e3, 0.0, 30.0, nan, inf, -inf]}


class TestEqualFilterFloat(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("F", 2.0)
    STRING = "F == 2.0"
    RESULT = [3]


class TestEqualFilterFloatPositiveInf(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("F", inf)
    STRING = "F == inf"
    RESULT = [8]


class TestEqualFilterFloatNegativeInf(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("F", -inf)
    STRING = "F == -inf"
    RESULT = [9]


class TestEqualFilterFloatNaN(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = EqualFilter
    ARGS = ("F", nan)
    STRING = "F == nan"
    RESULT = []


class TestIsNanFilter(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = IsNanFilter
    ARGS = ("F",)
    STRING = "F IS NaN"
    RESULT = [7]


class TestNotEqualFilterFloat(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("F", 2.0)
    STRING = "F != 2.0"
    RESULT = [0, 1, 2, 4, 5, 6, 7, 8, 9]


class TestNotEqualFilterFloatPositiveInf(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("F", inf)
    STRING = "F != inf"
    RESULT = [0, 1, 2, 3, 4, 5, 6, 7, 9]


class TestNotEqualFilterFloatNegativeInf(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("F", -inf)
    STRING = "F != -inf"
    RESULT = [0, 1, 2, 3, 4, 5, 6, 7, 8]


class TestNotEqualFilterFloatNaN(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = NotEqualFilter
    ARGS = ("F", nan)
    STRING = "F != nan"
    RESULT = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


class TestIsNotNanFilter(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = IsNotNanFilter
    ARGS = ("F",)
    STRING = "F IS NOT NaN"
    RESULT = [0, 1, 2, 3, 4, 5, 6, 8, 9]


class TestLessThanFilterFloat(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = LessThanFilter
    ARGS = ("F", 2.0)
    STRING = "F < 2.0"
    RESULT = [1, 2, 5, 9]


class TestGreaterThanFilterFloat(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = GreaterThanFilter
    ARGS = ("F", 2.0)
    STRING = "F > 2.0"
    RESULT = [0, 4, 6, 8]


class TestLessThanOrEqualFilterFloat(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = LessThanOrEqualFilter
    ARGS = ("F", 2)
    STRING = "F <= 2"
    RESULT = [1, 2, 3, 5, 9]


class TestGreaterThanOrEqualFilterFloat(TestCase, FloatTestMixIn, FilterTestMixIn):
    CLASS = GreaterThanOrEqualFilter
    ARGS = ("F", 2)
    STRING = "F >= 2"
    RESULT = [0, 3, 4, 6, 8]

# -----------------------------------------------------------------------------

class StringTestMixIn:
    REQUIRED_VARIABLES = ("U",)
    DATA = {"U": ["8I1y", "kWBV", "Z7I5", "ebMr", "nIeg"]}


class TestStringEqualFilterString(TestCase, StringTestMixIn, FilterTestMixIn):
    CLASS = StringEqualFilter
    ARGS = ("U", "ebMr")
    STRING = "U == 'ebMr'"
    RESULT = [3]


class TestStringNotEqualFilterString(TestCase, StringTestMixIn, FilterTestMixIn):
    CLASS = StringNotEqualFilter
    ARGS = ("U", "ebMr")
    STRING = "U != 'ebMr'"
    RESULT = [0, 1, 2, 4]

# -----------------------------------------------------------------------------

class BytesTestMixIn:
    REQUIRED_VARIABLES = ("A",)
    DATA = {"A": [b"8I1y", b"kWBV", b"Z7I5", b"ebMr", b"nIeg"]}


class TestStringEqualFilterBytes(TestCase, BytesTestMixIn, FilterTestMixIn):
    CLASS = StringEqualFilter
    ARGS = ("A", "ebMr")
    STRING = "A == 'ebMr'"
    RESULT = [3]


class TestStringNotEqualFilterBytes(TestCase, BytesTestMixIn, FilterTestMixIn):
    CLASS = StringNotEqualFilter
    ARGS = ("A", "ebMr")
    STRING = "A != 'ebMr'"
    RESULT = [0, 1, 2, 4]


class TestStringEqualFilterBytesAlt(TestCase, BytesTestMixIn, FilterTestMixIn):
    CLASS = StringEqualFilter
    ARGS = ("A", b"ebMr")
    STRING = "A == b'ebMr'"
    RESULT = [3]


class TestStringNotEqualFilterBytesAlt(TestCase, BytesTestMixIn, FilterTestMixIn):
    CLASS = StringNotEqualFilter
    ARGS = ("A", b"ebMr")
    STRING = "A != b'ebMr'"
    RESULT = [0, 1, 2, 4]

# -----------------------------------------------------------------------------

class BitflagsTestMixIn:
    REQUIRED_VARIABLES = ("M",)
    DATA = {"M": [9, 7, 0, 5, 3, 8, 15, 6, 2, 12, 13, 1, 4, 11, 14, 10]}


class TestBitmaskEqualFilter(TestCase, BitflagsTestMixIn, FilterTestMixIn):
    CLASS = BitmaskEqualFilter
    ARGS = ("M", 6, 3)
    STRING = "M & 6 == 2"
    RESULT = [4,  8, 13, 15]

class TestBitmaskNotEqualFilter(TestCase, BitflagsTestMixIn, FilterTestMixIn):
    CLASS = BitmaskNotEqualFilter
    ARGS = ("M", 6, 3)
    STRING = "M & 6 != 2"
    RESULT = [ 0,  1,  2,  3,  5,  6,  7,  9, 10, 11, 12, 14]

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
