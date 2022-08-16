#-------------------------------------------------------------------------------
#
#  Data filters - single variable predicates
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

from numpy import (
    char, bytes_, unicode_,
    equal, not_equal, isnan,
)
from .base import Filter
from .utils import format_variable, get_data


class SingleVariablePredicate(Filter):
    """ Single variable predicate. """

    @property
    def formatted_variable(self):
        """ Get nicely formatted variable. """
        return format_variable(self.variable, self.index)

    @property
    def required_variables(self):
        return (self.variable,)

    def __init__(self, variable):
        self.variable, self.index = (
            (variable, ()) if isinstance(variable, str) else variable
        )

    def filter(self, dataset, index=None):
        data = get_data(dataset, self.variable, self.index)

        self._check_types(self, data)

        if index is None:
            index = self._filter(data).nonzero()[0]
        else:
            index = index[self._filter(data[index])]
        return index

    @staticmethod
    def _check_types(data, value):
        """ Override this method to implement an extra type check. """

    def _filter(self, data):
        """ This is the actual filter function. For the given data array it
        returns the result of the comparison as a Boolen array (True - value
        selected, False - value rejected.
        """
        raise NotImplementedError


class BitmaskEqualFilter(SingleVariablePredicate):
    """ Bitmask selection filter (variable & mask == value & mask) """

    @property
    def key(self):
        return (self.__class__, (self.variable, self.index), self.mask, self.value)

    def __init__(self, variable, mask, value):
        super().__init__(variable)
        self.value = mask & value
        self.mask = mask

    def _filter(self, data):
        return data & self.mask == self.value

    def __str__(self):
        return f"{self.formatted_variable} & {self.mask} == {self.value}"


class BitmaskNotEqualFilter(SingleVariablePredicate):
    """ Bitmask selection filter (variable & mask != value & mask) """

    @property
    def key(self):
        return (self.__class__, (self.variable, self.index), self.mask, self.value)

    def __init__(self, variable, mask, value):
        super().__init__(variable)
        self.value = mask & value
        self.mask = mask

    def _filter(self, data):
        return data & self.mask != self.value

    def __str__(self):
        return f"{self.formatted_variable} & {self.mask} != {self.value}"


class SingleValuePredicate(SingleVariablePredicate):
    """ Base filters class comparing single value with a single scalar array.
    """
    @property
    def key(self):
        return (self.__class__, (self.variable, self.index), self.value)

    def __init__(self, variable, value):
        super().__init__(variable)
        self.value = value


class EqualFilter(SingleValuePredicate):
    """ Scalar value equality filter (variable == value) """
    def _filter(self, data):
        return equal(data, self.value)

    def __str__(self):
        return f"{self.formatted_variable} == {self.value!r}"


class NotEqualFilter(SingleValuePredicate):
    """ Scalar value non-equality filter (variable != value) """
    def _filter(self, data):
        return not_equal(data, self.value)

    def __str__(self):
        return f"{self.formatted_variable} != {self.value!r}"


class StringEqualFilter(SingleValuePredicate):
    """ Scalar value string equality filter (variable == value) """
    def _filter(self, data):
        value = self.value
        if data.dtype.type == bytes_:
            if isinstance(value, str):
                value = value.encode("utf8")
        return char.equal(data, value)

    def __str__(self):
        return f"{self.formatted_variable} == {self.value!r}"


class StringNotEqualFilter(SingleValuePredicate):
    """ Scalar stirng value equality filter (variable != value) """
    def _filter(self, data):
        value = self.value
        if data.dtype.type == bytes_:
            if isinstance(value, str):
                value = value.encode("utf8")
        return char.not_equal(data, value)

    def __str__(self):
        return f"{self.formatted_variable} != {self.value!r}"


class LessThanFilter(SingleValuePredicate):
    """ Scalar value less-than filter (variable < value) """
    def _filter(self, data):
        return data < self.value

    def __str__(self):
        return f"{self.formatted_variable} < {self.value!r}"


class GreaterThanFilter(SingleValuePredicate):
    """ Scalar value greater-than filter (variable > value) """
    def _filter(self, data):
        return data > self.value

    def __str__(self):
        return f"{self.formatted_variable} > {self.value!r}"


class LessThanOrEqualFilter(SingleValuePredicate):
    """ Scalar value less-than-or-equal filter (variable <= value) """
    def _filter(self, data):
        return data <= self.value

    def __str__(self):
        return f"{self.formatted_variable} <= {self.value!r}"


class GreaterThanOrEqualFilter(SingleValuePredicate):
    """ Scalar value greater-than-or-equal filter (variable >= value) """
    def _filter(self, data):
        return data >= self.value

    def __str__(self):
        return f"{self.formatted_variable} >= {self.value!r}"


class IsNanFilter(SingleVariablePredicate):
    """ Select NaN values (variable is NaN) """
    @property
    def key(self):
        return (self.__class__, (self.variable, self.index))

    def _filter(self, data):
        return isnan(data)

    def __str__(self):
        return f"{self.formatted_variable} IS NaN"


class IsNotNanFilter(SingleVariablePredicate):
    """ Select NaN values (variable is not NaN) """
    @property
    def key(self):
        return (self.__class__, (self.variable, self.index))

    def _filter(self, data):
        return ~isnan(data)

    def __str__(self):
        return f"{self.formatted_variable} IS NOT NaN"
