#-------------------------------------------------------------------------------
#
#  Data filters - bounding box filter
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
# pylint: disable=too-many-arguments

from .boolean_operations import Conjunction
from .simple_predicates import LessThanOrEqualFilter, GreaterThanOrEqualFilter


class BoundingBoxFilter(Conjunction):
    """ Bounding box filter. """

    def __init__(self, variable1, variable2, bbox):
        (min_value1, min_value2), (max_value1, max_value2) = bbox
        super().__init__(
            GreaterThanOrEqualFilter(variable1, min_value1),
            LessThanOrEqualFilter(variable1, max_value1),
            GreaterThanOrEqualFilter(variable2, min_value2),
            LessThanOrEqualFilter(variable2, max_value2),
        )
