#-------------------------------------------------------------------------------
#
# Process Utilities - filters input parsers
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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

import re
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from ..filters import ScalarRangeFilter, VectorComponentRangeFilter


RE_FILTER_NAME = re.compile(r'(^[^[]+)(?:\[([0-9])\])?$')


def parse_filters(input_id, filter_string):
    """ Parse filters' string and return list of the filter objects. """

    def _get_filter(name, vmin, vmax):
        match = RE_FILTER_NAME.match(name)
        if match is None:
            raise InvalidInputValueError(
                input_id, "Invalid filter name %r" % name
            )
        variable, component = match.groups()
        if component is None:
            return ScalarRangeFilter(variable, vmin, vmax)
        return VectorComponentRangeFilter(
            variable, int(component), vmin, vmax
        )

    try:
        return [
            _get_filter(name, vmin, vmax) for name, (vmin, vmax)
            in _parse_filter_string(filter_string)
        ]
    except ValueError as exc:
        raise InvalidInputValueError(input_id, exc)


def _parse_filter_string(filter_string):
    filters = set()
    if filter_string.strip():
        for item in filter_string.split(";"):
            name, bounds = item.split(":")
            name = name.strip()
            if not name:
                raise ValueError("Invalid empty filter name!")
            lower, upper = [float(v) for v in bounds.split(",")]
            if name in filters:
                raise ValueError("Duplicate filter %r!" % name)
            filters.add(name)
            yield name, (lower, upper)
