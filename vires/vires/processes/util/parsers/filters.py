#-------------------------------------------------------------------------------
#
# Process Utilities - filters input parsers
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2022 EOX IT Services GmbH
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
# pylint: disable=too-many-branches,unused-argument

from math import isnan
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.parsers.exceptions import ParserError
from vires.parsers.filters_parser import get_filters_parser
from vires.parsers.filters_lexer import get_filters_lexer
from vires.util import unique
from vires.filters import (
    Negation,
    Conjunction,
    Disjunction,
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


def parse_filters(input_id, filter_string):
    """ Parse filters' string and return list of the filter objects. """
    try:
        return _FiltersParser.parse_filters(filter_string)
    except _FiltersParser.ParsingError as error:
        raise InvalidInputValueError(input_id, str(error)) from None


class _FiltersParser:
    """ Class parsing filters input. """

    class ParsingError(Exception):
        """ Model parsing error. """

    # disctionary of registered filter constructors
    FILTER_CONSTRUCTORS = {}

    @classmethod
    def filter_constructor(cls, name):
        """ Decorator registering filter constructor. """
        def _add_filter_constructor(constructor):
            cls.FILTER_CONSTRUCTORS[name] = constructor
            return constructor
        return _add_filter_constructor

    @classmethod
    def construct_filter(cls, name, *args):
        """ Construct filter object from the given parsed predicate.
        """
        return cls.FILTER_CONSTRUCTORS[name](*args)

    @classmethod
    def construct_filters(cls, predicates):
        """ Construct unique filters from the given list of parsed predicates.
        """
        return list(unique(
            cls.construct_filter(*predicate) for predicate in predicates
        ))

    @classmethod
    def parse_filters(cls, filter_string):
        """ Parse filter string. """
        return cls.construct_filters(cls._parse_filters_string(filter_string))

    @classmethod
    def _parse_filters_string(cls, filters_string):
        if filters_string is None:
            return []

        lexer = get_filters_lexer()
        parser = get_filters_parser()
        try:
            root = parser.parse(filters_string, lexer=lexer)
        except ParserError as error:
            raise cls.ParsingError(f"Invalid filter specification! {error}")

        if not root: # no filter
            return []

        if root[0] == "conjunction": # expand conjunction
            return root[1]

        return [root] # predicate is not conjuction


@_FiltersParser.filter_constructor("not")
def _create_negated_filter(predicate):
    return Negation(_FiltersParser.construct_filter(*predicate))


@_FiltersParser.filter_constructor("conjunction")
def _create_conjunction_filter(predicates):
    filters = _FiltersParser.construct_filters(predicates)
    return filters[0] if len(filters) == 1 else Conjunction(*filters)


@_FiltersParser.filter_constructor("disjunction")
def _create_disjunction_filter(predicates):
    filters = _FiltersParser.construct_filters(predicates)
    return filters[0] if len(filters) == 1 else Disjunction(*filters)


@_FiltersParser.filter_constructor("equal")
def _create_equal_filter(variable, value):
    if isinstance(value, str):
        class_ = StringEqualFilter
    elif isinstance(value, float) and isnan(value):
        class_ = IsNanFilter
    else:
        class_ = EqualFilter
    return class_(variable, value)


@_FiltersParser.filter_constructor("not_equal")
def _create_not_equal_filter(variable, value):
    class_ = StringNotEqualFilter if isinstance(value, str) else NotEqualFilter
    if isinstance(value, str):
        class_ = StringNotEqualFilter
    elif isinstance(value, float) and isnan(value):
        class_ = IsNotNanFilter
    else:
        class_ = NotEqualFilter
    return class_(variable, value)


_FiltersParser.filter_constructor("bitmask_equal")(BitmaskEqualFilter)
_FiltersParser.filter_constructor("bitmask_not_equal")(BitmaskNotEqualFilter)
_FiltersParser.filter_constructor("greater_than")(GreaterThanFilter)
_FiltersParser.filter_constructor("greater_than_or_equal")(GreaterThanOrEqualFilter)
_FiltersParser.filter_constructor("less_than")(LessThanFilter)
_FiltersParser.filter_constructor("less_than_or_equal")(LessThanOrEqualFilter)
