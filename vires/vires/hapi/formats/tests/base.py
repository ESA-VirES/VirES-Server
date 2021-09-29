#-------------------------------------------------------------------------------
#
# VirES HAPI - format encoding / decoding - base test mixin
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

import string
from random import choice
from numpy import array, prod, dtype, iinfo, datetime64
from numpy.random import uniform, randint

ASCII_ALPHANUMERIC = (
    string.ascii_uppercase + string.ascii_lowercase + string.digits
) + "\n,\""
ASCII_ALPHANUMERIC_BYTES = ASCII_ALPHANUMERIC.encode("ascii")


class FormatTestMixIn():

    def _test(self, *arrays, dump=False):
        raise NotImplementedError

    def test_mixed_arrays(self):
        self._test(
            random_string_array((20,), 4),
            random_integer_array((20, 3), "int32"),
            random_float_array((20, 2, 3), "float64"),
        )

    def test_datetime64_year(self):
        self._test(random_datetime64_array((20,), "Y"))

    def test_datetime64_month(self):
        self._test(random_datetime64_array((20,), "M"))

    def test_datetime64_week(self):
        self._test(random_datetime64_array((20,), "W"))

    def test_datetime64_day(self):
        self._test(random_datetime64_array((20,), "D"))

    def test_datetime64_hour(self):
        self._test(random_datetime64_array((20,), "h"))

    def test_datetime64_minute(self):
        self._test(random_datetime64_array((20,), "m"))

    def test_datetime64_second(self):
        self._test(random_datetime64_array((20,), "s"))

    def test_datetime64_millisecond(self):
        self._test(random_datetime64_array((20,), "ms"))

    def test_datetime64_microsecond(self):
        self._test(random_datetime64_array((20,), "us"))

    def test_bytes_array_0d(self):
        self._test(random_bytes_array((20,), 7))

    def test_bytes_array_1d(self):
        self._test(random_bytes_array((20, 5), 7))

    def test_bytes_array_2d(self):
        self._test(random_bytes_array((20, 5, 3), 7))

    def test_string_array_0d(self):
        self._test(random_string_array((20,), 4))

    def test_string_array_1d(self):
        self._test(random_string_array((20, 5), 4))

    def test_string_array_2d(self):
        self._test(random_string_array((20, 5, 3), 4))

    def test_float32_special_values(self):
        self._test(array(["-inf", "nan", "inf"], "float32"))

    def test_float32_array_0d(self):
        self._test(random_float_array((20,), "float32"))

    def test_float32_array_1d(self):
        self._test(random_float_array((20, 5), "float32"))

    def test_float32_array_2d(self):
        self._test(random_float_array((20, 5, 3), "float32"))

    def test_float64_special_values(self):
        self._test(array(["-inf", "nan", "inf"], "float64"))

    def test_float64_array_0d(self):
        self._test(random_float_array((20,), "float64"))

    def test_float64_array_1d(self):
        self._test(random_float_array((20, 5), "float64"))

    def test_float64_array_2d(self):
        self._test(random_float_array((20, 5, 3), "float64"))

    def test_bool_array_0d(self):
        self._test(random_float_array((20,), "float32") >= 0)

    def test_uint8_array_0d(self):
        self._test(random_integer_array((20,), 'uint8'))

    def test_uint16_array_0d(self):
        self._test(random_integer_array((20,), 'uint16'))

    def test_uint32_array_0d(self):
        self._test(random_integer_array((20,), 'uint32'))

    def test_uint64_array_0d(self):
        self._test(random_integer_array((20,), 'uint64'))

    def test_int8_array_0d(self):
        self._test(random_integer_array((20,), 'int8'))

    def test_int16_array_0d(self):
        self._test(random_integer_array((20,), 'int16'))

    def test_int32_array_0d(self):
        self._test(random_integer_array((20,), 'int32'))

    def test_int64_array_0d(self):
        self._test(random_integer_array((20,), 'int64'))


def random_string_array(shape, size=1, alphabet=ASCII_ALPHANUMERIC):
    def _random_string():
        return "".join([choice(alphabet) for _ in range(size)])
    return array([_random_string() for _ in range(prod(shape))]).reshape(*shape)


def random_bytes_array(shape, size=1, alphabet=ASCII_ALPHANUMERIC_BYTES):
    def _random_string():
        return bytes([(choice(alphabet)) for _ in range(size)])
    return array([_random_string() for _ in range(prod(shape))]).reshape(*shape)


def random_float_array(shape, type_, vmin=-1.0, vmax=1.0):
    return uniform(vmin, vmax, shape).astype(type_)


def random_integer_array(shape, type_):
    type_ = dtype(type_)
    return randint(iinfo(type_).min, iinfo(type_).max, shape, type_)


def random_datetime64_array(shape, unit, base="2020-01-01T00:00:00",
                            dtmin=-1000, dtmax=1001):
    return (
        datetime64(base, unit) +
        randint(dtmin, dtmax, shape).astype(f"timedelta64[{unit}]")
    )
