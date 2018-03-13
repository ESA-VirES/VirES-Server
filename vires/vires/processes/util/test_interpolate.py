#-------------------------------------------------------------------------------
#
# Testing Interp1D
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
# pylint: disable=missing-docstring, invalid-name

from logging import getLogger, Formatter, StreamHandler, DEBUG
import unittest
from numpy import array, arange, isnan, nan
from interpolate import Interp1D
from vires.tests import ArrayMixIn

NAN = float('NaN')


def set_stream_handler(logger, level=DEBUG):
    """ Set stream handler to the logger. """
    formatter = Formatter('%(levelname)s: %(module)s: %(message)s')
    handler = StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(min(level, logger.level))


class TestInterp1D(ArrayMixIn, unittest.TestCase):

    def assertEqualArrays(self, res, ref):
        """ Check arrays equality. """
        if res.shape != ref.shape:
            raise ValueError("Shape mismatch!")
        self.assertAllEqual(isnan(res), isnan(ref))
        self.assertAllEqual(res[~isnan(res)], ref[~isnan(ref)])

    def testNearestValid(self):
        x_src = array([1.0, 2.0, 3.0])
        x_dst = array([0.0, 1.2, 1.6, 2.4, 2.6, 4.0])

        y_src = arange(len(x_src))
        z_src = arange(len(x_src), 0, -1)
        v_src = arange(len(x_src)*2).reshape((len(x_src), 2))

        y_dst = array([NAN, 0.0, 1.0, 1.0, 2.0, NAN])
        z_dst = array([NAN, 3.0, 2.0, 2.0, 1.0, NAN])
        v_dst = array([
            (NAN, NAN), (0.0, 1.0), (2.0, 3.0),
            (2.0, 3.0), (4.0, 5.0), (NAN, NAN),
        ])

        interp1d = Interp1D(x_src, x_dst)
        kind = "nearest"
        self.assertEqualArrays(interp1d(y_src, kind), y_dst)
        self.assertEqualArrays(interp1d(z_src, kind), z_dst)
        self.assertEqualArrays(interp1d(v_src, kind), v_dst)

    def testNearestValidEmpty(self):
        x_src = array([1.0, 2.0, 3.0])
        x_dst = array([])

        y_src = arange(len(x_src))
        z_src = arange(len(x_src), 0, -1)
        v_src = arange(len(x_src)*2).reshape((len(x_src), 2))

        y_dst = array([])
        z_dst = array([])
        v_dst = array([]).reshape((0, 2))

        interp1d = Interp1D(x_src, x_dst)
        kind = "nearest"
        self.assertEqualArrays(interp1d(y_src, kind), y_dst)
        self.assertEqualArrays(interp1d(z_src, kind), z_dst)
        self.assertEqualArrays(interp1d(v_src, kind), v_dst)

    def testNearestWithGap(self):
        x_src = array([1.0, 2.0, 3.0, 5.0, 6.0])
        y_src = array([2.0, 1.0, 0.5, 1.5, 2.5])
        x_dst = array([0.5, 1.0, 1.6, 2.7, 3.0, 3.5, 4.5, 5.2, 5.9, 7.0])
        y_dst = array([nan, 2.0, 1.0, 0.5, 0.5, nan, nan, 1.5, 2.5, nan])
        interp1d = Interp1D(x_src, x_dst, 1.5)
        kind = "nearest"
        self.assertEqualArrays(interp1d(y_src, kind), y_dst)

    def testNearestWithGapAndInvalidSegments(self):
        x_src = array([-1.0, 1.0, 2.0, 3.0, 5.0])
        y_src = array([4.0, 2.0, 1.0, 0.5, 1.5])
        x_dst = array([-1.5, 0.5, 1.0, 1.6, 2.7, 3.0, 3.5, 4.5, 5.2, 5.9])
        y_dst = array([nan, nan, 2.0, 1.0, 0.5, 0.5, nan, nan, nan, nan])
        interp1d = Interp1D(x_src, x_dst, 1.5)
        kind = "nearest"
        self.assertEqualArrays(interp1d(y_src, kind), y_dst)

    def testNotEnoughValuesSingle(self):
        x_src = array([1.0])
        x_dst = array([0.0, 1.0, 2.0])
        y_src = arange(len(x_src))
        y_dst = array([nan, nan, nan])
        interp1d = Interp1D(x_src, x_dst)
        kind = "nearest"
        self.assertEqualArrays(interp1d(y_src, kind), y_dst)

    def testNotEnoughValuesEmpty(self):
        x_src = array([])
        x_dst = array([0.0, 1.0, 2.0])
        y_src = arange(len(x_src))
        y_dst = array([nan, nan, nan])
        interp1d = Interp1D(x_src, x_dst)
        kind = "nearest"
        self.assertEqualArrays(interp1d(y_src, kind), y_dst)

    def testLenghtMismatch(self):
        x_src = array([1.0, 2.0, 3.0])
        x_dst = array([0.0, 1.0, 2.0])
        y_src = arange(len(x_src) + 1)
        interp1d = Interp1D(x_src, x_dst)
        kind = "nearest"
        self.assertRaises(ValueError, interp1d, y_src, kind)


if __name__ == "__main__":
    set_stream_handler(getLogger())
    unittest.main()
