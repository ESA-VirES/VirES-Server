#-------------------------------------------------------------------------------
#
#  Data filters - common testing utilities
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

from numpy import array, intersect1d
from numpy.random import randint
from numpy.testing import assert_equal
from vires.util import cached_property
from vires.dataset import Dataset


class FilterTestMixIn:
    STRING = ""
    CLASS = type
    ARGS = ()
    KWARGS = {}
    REQUIRED_VARIABLES = ()
    DATA = {}
    RESULT = []

    @cached_property
    def filter(self):
        return self.CLASS(*self.ARGS, **self.KWARGS)

    @cached_property
    def data(self):
        dataset = Dataset()
        for variable, data in self.DATA.items():
            dataset.set(variable, array(data))
        return dataset

    @cached_property
    def result(self):
        return array(self.RESULT, "int64")

    def test_class(self):
        self.assertTrue(isinstance(self.filter, self.CLASS))

    def test_hashability(self):
        self.assertTrue(len(set([self.filter, self.filter])) == 1)

    def test_equality(self):
        self.assertTrue(self.filter == self.filter)

    def test_string(self):
        self.assertEqual(str(self.filter), self.STRING)

    def test_required_variables(self):
        self.assertEqual(
            set(self.filter.required_variables), set(self.REQUIRED_VARIABLES)
        )

    def test_filter(self):
        assert_equal(self.filter.filter(self.data), self.result)

    def test_filter_with_index(self):
        index = randint(2, size=self.data.length).nonzero()[0]
        assert_equal(self.filter.filter(self.data, index), intersect1d(self.result, index))
