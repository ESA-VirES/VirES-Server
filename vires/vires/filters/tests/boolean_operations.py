#-------------------------------------------------------------------------------
#
#  Data filters - composed predicates - Boolean operations - tests
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
from vires.filters import (
    Negation,
    Conjunction,
    Disjunction,
    EqualFilter,
    GreaterThanOrEqualFilter,
)
from vires.filters.tests.common import FilterTestMixIn


class TestNegation(TestCase, FilterTestMixIn):
    CLASS = Negation
    ARGS = (EqualFilter("I", 2),)
    REQUIRED_VARIABLES = ("I",)
    DATA = {"I": [4, -1, 1, 2, 5, 0, 3]}
    STRING = "NOT I == 2"
    RESULT = [0, 1, 2, 4, 5, 6]


class TestConjunction(TestCase, FilterTestMixIn):
    CLASS = Conjunction
    ARGS = (
        GreaterThanOrEqualFilter("I", 1),
        GreaterThanOrEqualFilter("J", 2),
    )
    REQUIRED_VARIABLES = ("I", "J")
    DATA = {
        "I": [4, -1, 1, 2, 5, 0, 3],
        "J": [5, 4, -1, 2, 1, 0, 3],
    }
    STRING = "(I >= 1 AND J >= 2)"
    RESULT = [0, 3, 6]


class TestDisjunction(TestCase, FilterTestMixIn):
    CLASS = Disjunction
    ARGS = (
        EqualFilter("I", -1),
        EqualFilter("I", 0),
        EqualFilter("J", 2),
        EqualFilter("J", 5),
    )
    REQUIRED_VARIABLES = ("I", "J")
    DATA = {
        "I": [4, -1, 1, 2, 5, 0, 3],
        "J": [5, 4, -1, 2, 1, 0, 3],
    }
    STRING = "(I == -1 OR I == 0 OR J == 2 OR J == 5)"
    RESULT = [0, 1, 3, 5]


if __name__ == "__main__":
    main()
