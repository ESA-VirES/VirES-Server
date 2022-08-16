#-------------------------------------------------------------------------------
#
#  Data filters - composed predicates - Boolean operations
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

from itertools import chain
from numpy import empty, full, setdiff1d, union1d
from .base import Filter


class Negation(Filter):
    """ NOT operator. """

    @property
    def key(self):
        return (self.__class__, self.predicate)

    def __str__(self):
        return f"NOT {self.predicate}"

    @property
    def required_variables(self):
        return self.predicate.required_variables

    def __init__(self, predicate):
        self.predicate = predicate

    def filter(self, dataset, index=None):
        if index is not None:
            return setdiff1d(index, self.predicate.filter(dataset, index))
        mask = full(dataset.length, True)
        mask[self.predicate.filter(dataset)] = False
        return mask.nonzero()[0]


class Conjunction(Filter):
    """ AND operator. """

    @property
    def key(self):
        return (self.__class__, frozenset(self.predicates))

    def __str__(self):
        predicates = " AND ".join(
            str(predicate) for predicate in self.predicates
        )
        return f"({predicates})"

    @property
    def required_variables(self):
        return self._required_variables

    def __init__(self, predicate, *other_predicates):
        self.predicates = (predicate, *other_predicates)
        self._required_variables = tuple(set(chain.from_iterable(
            predicate.required_variables for predicate in self.predicates
        )))

    def filter(self, dataset, index=None):
        for predicate in self.predicates:
            if index is not None and index.size == 0:
                break
            index = predicate.filter(dataset, index)
        return index


class Disjunction(Filter):
    """ OR operator. """

    @property
    def key(self):
        return (self.__class__, frozenset(self.predicates))

    def __str__(self):
        predicates = " OR ".join(
            str(predicate) for predicate in self.predicates
        )
        return f"({predicates})"

    @property
    def required_variables(self):
        return self._required_variables

    def __init__(self, predicate, *other_predicates):
        self.predicates = [predicate, *other_predicates]
        self._required_variables = tuple(set(chain.from_iterable(
            predicate.required_variables for predicate in self.predicates
        )))

    def filter(self, dataset, index=None):
        new_index = empty(0, 'int')
        for predicate in self.predicates:
            new_index = union1d(new_index, predicate.filter(dataset, index))
        return new_index
