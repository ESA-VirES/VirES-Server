#-------------------------------------------------------------------------------
#
#  Data filters - bounding box filter - test
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

from unittest import TestCase, main
from vires.filters import BoundingBoxFilter
from vires.filters.tests.common import FilterTestMixIn


class TestBoundingBoxFilter(TestCase, FilterTestMixIn):
    CLASS = BoundingBoxFilter
    ARGS = ("Latitude", "Longitude", ((-45, -90), (+45, +90)))
    REQUIRED_VARIABLES = ("Latitude", "Longitude")
    DATA = {
        "Latitude": [-90., -45., 0., +45., +90.],
        "Longitude": [-180., -90, 0., +90., +180.],
    }
    STRING = "(Latitude >= -45 AND Latitude <= 45 AND Longitude >= -90 AND Longitude <= 90)"
    RESULT = [1, 2, 3]


if __name__ == "__main__":
    main()
