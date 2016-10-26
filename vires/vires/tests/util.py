#-------------------------------------------------------------------------------
#
# Testing utilities.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=missing-docstring

import unittest
from datetime import timedelta, datetime
from numpy import array
from matplotlib.colors import LinearSegmentedColormap
from vires.tests import ArrayMixIn
from vires.util import (
    between, between_co, float_array_slice, datetime_array_slice,
    get_total_seconds, get_color_scale, get_model,
)

class TestUtil(ArrayMixIn, unittest.TestCase):
    # NOTE: The IGRF12 and SIFM models are broken!
    MODELS = [
        "CHAOS-5-Combined", "WMM", "WMM2010", "WMM2015", "EMM", "EMM2010",
        "IGRF", "IGRF11", "IGRF12", "SIFM",
    ]

    COLOR_MAPS = [
        "blackwhite", "coolwarm", "rainbow", "custom2", "custom1",
        "prism",
    ]

    def test_color_scale(self):
        for cm_id in self.COLOR_MAPS:
            try:
                self.assertTrue(
                    isinstance(get_color_scale(cm_id), LinearSegmentedColormap)
                )
            except:
                print "Test failed for colormap %r!" % cm_id
                raise

        with self.assertRaises(ValueError):
            get_color_scale("-invalid-")

    def test_model(self):
        for model_id in self.MODELS:
            try:
                self.assertTrue(get_model(model_id) is not None)
            except:
                print "Test failed for model %r!" % model_id
                raise
        self.assertTrue(get_model("-invalid-model-") is None)

    def test_between(self):
        self.assertAllEqual(
            between(array([1.0, 1.5, 2.0, 3.0, 3.5, 4.0]), 1.5, 3.5),
            array([False, True, True, True, True, False])
        )

    def test_between_co(self):
        self.assertAllEqual(
            between_co(array([1.0, 1.5, 2.0, 3.0, 3.5, 4.0]), 1.5, 3.5),
            array([False, True, True, True, False, False])
        )

    def test_total_seconds(self):
        self.assertAlmostEqual(
            get_total_seconds(
                datetime(2016, 3, 30, 1, 1, 1, 1001) - datetime(2016, 3, 29)
            ), 90061.001001, delta=1e-7
        )
        self.assertAlmostEqual(
            get_total_seconds(
                datetime(2016, 3, 27, 22, 58, 58, 998999) -
                datetime(2016, 3, 29)
            ), -90061.001001, delta=1e-7
        )

    def test_float_array_slice(self):

        def test_ascending(start, stop, low, high):
            self.assertEqual(
                float_array_slice(start, stop, 1.0, 2.0, 0.1, 1e-6),
                (low, high)
            )

        def test_descending(start, stop, low, high):
            self.assertEqual(
                float_array_slice(start, stop, -1.0, -2.0, -0.1, 1e-6),
                (low, high)
            )

        # ascending order ...
        # total overlap
        test_ascending(0.0, 3.0, 0, 11)
        test_ascending(1.0, 2.0, 0, 11)
        test_ascending(1.0 + 1e-7, 2.0 - 1e-7, 0, 11)
        # partial overlap
        test_ascending(1.25, 1.75, 3, 8)
        test_ascending(0.25, 1.75, 0, 8)
        test_ascending(1.25, 2.75, 3, 11)
        test_ascending(0.25, 1.0, 0, 1)
        test_ascending(2.0, 2.75, 10, 11)
        test_ascending(1.45, 1.55, 5, 6)
        # no overlap
        test_ascending(0.25, 0.75, 0, 0)
        test_ascending(2.25, 2.75, 0, 0)
        test_ascending(1.24, 1.26, 3, 3)
        # descending order ...
        # total overlap
        test_descending(0.0, -3.0, 0, 11)
        test_descending(-1.0, -2.0, 0, 11)
        test_descending(-1.0 + 1e-7, -2.0 - 1e-7, 0, 11)
        # partial overlap
        test_descending(-1.25, -1.75, 3, 8)
        test_descending(-0.25, -1.75, 0, 8)
        test_descending(-1.25, -2.75, 3, 11)
        test_descending(-0.25, -1.0, 0, 1)
        test_descending(-2.0, -2.75, 10, 11)
        test_descending(-1.45, -1.55, 5, 6)
        # no overlap
        test_descending(-0.25, -0.75, 0, 0)
        test_descending(-2.25, -2.75, 0, 0)
        test_descending(-1.24, -1.26, 3, 3)

    def test_time_array_slice(self):

        def test_ascending(start, stop, low, high):
            first = datetime(2016, 3, 29)
            last = datetime(2016, 3, 30)
            step = timedelta(seconds=3600)
            tolerance = timedelta(seconds=60)
            self.assertEqual(
                datetime_array_slice(start, stop, first, last, step, tolerance),
                (low, high)
            )

        # total overlap
        delta = timedelta(seconds=30)
        test_ascending(datetime(2016, 3, 28), datetime(2016, 3, 31), 0, 25)
        test_ascending(datetime(2016, 3, 29), datetime(2016, 3, 30), 0, 25)
        test_ascending(
            datetime(2016, 3, 29) - delta, datetime(2016, 3, 30) + delta,
            0, 25
        )
        # partial overlap
        test_ascending(
            datetime(2016, 3, 29, 3, 30), datetime(2016, 3, 29, 20, 30), 4, 21
        )
        test_ascending(
            datetime(2016, 3, 28), datetime(2016, 3, 29, 20, 30), 0, 21
        )
        test_ascending(
            datetime(2016, 3, 29, 3, 30), datetime(2016, 3, 31), 4, 25
        )
        test_ascending(datetime(2016, 3, 28), datetime(2016, 3, 29), 0, 1)
        test_ascending(datetime(2016, 3, 30), datetime(2016, 3, 31), 24, 25)
        test_ascending(
            datetime(2016, 3, 29, 5, 30), datetime(2016, 3, 29, 6, 30), 6, 7
        )
        # no overlap
        test_ascending(
            datetime(2016, 3, 28), datetime(2016, 3, 28, 23, 0), 0, 0
        )
        test_ascending(
            datetime(2016, 3, 30, 1, 0), datetime(2016, 3, 31), 0, 0
        )
        test_ascending(
            datetime(2016, 3, 29, 3, 15), datetime(2016, 3, 29, 3, 45), 4, 4
        )


if __name__ == "__main__":
    unittest.main()
