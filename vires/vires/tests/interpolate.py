#-------------------------------------------------------------------------------
#
#  Testing gap-aware 1D interpolation.
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
# pylint: disable=missing-docstring,line-too-long

from unittest import TestCase, main
from logging import getLogger, DEBUG, INFO, Formatter, StreamHandler
from numpy import array, nan, empty, full
from numpy.testing import assert_allclose
from vires.tests import ArrayMixIn
from vires.interpolate import Interp1D

LOG_LEVEL = INFO

GLOBAL_X_DST = array([
    0, 3, 5, 7,
    10, 13, 15, 17, 20, 23, 25, 27, 30, 33, 35, 37,
    40, 43, 45, 47, 50, 53, 55, 57, 60, 63, 65, 67,
    70, 73, 75, 77, 80, 83, 85, 87, 90, 93, 95, 97,
])


def set_stream_handler(logger, level=DEBUG):
    """ Set stream handler to the logger. """
    formatter = Formatter('%(levelname)s: %(module)s: %(message)s')
    handler = StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(min(level, logger.level))

set_stream_handler(getLogger(), LOG_LEVEL)


class InterplateTestMixIn(ArrayMixIn):
    GAP_THRESHOLD = 10
    SEGMENT_NEIGHBOURHOOD = 0
    KIND = None
    X_SRC = None
    Y_SRC = None
    DY_SRC = None
    X_DST = None
    Y_DST = None

    def test_interp1d(self):
        x_src = array(self.X_SRC)
        y_src = array(self.Y_SRC)
        x_dst = array(self.X_DST)
        y_dst = array(self.Y_DST)
        dy_src = None if self.DY_SRC is None else array(self.DY_SRC)
        result = Interp1D(
            x_src, x_dst, self.GAP_THRESHOLD,
            self.SEGMENT_NEIGHBOURHOOD
        )(y_src, dy_src, kind=self.KIND)
        try:
            assert_allclose(result, y_dst, atol=1e-12)
        except:
            print()
            print(self.__class__.__name__)
            print("x_src:", x_src)
            print("x_dst:", x_dst)
            print("y_src:", y_src)
            print("dy_src:", dy_src)
            print("expected:", y_dst)
            print("received:", result)
            raise

#-------------------------------------------------------------------------------

class TestI1DErrors(TestCase):

    def test_size_mismatch(self):
        x_src = array([10, 20, 30, 40, 50, 60, 70, 80, 90])
        y_src = array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        x_dst = array(GLOBAL_X_DST)

        with self.assertRaises(ValueError):
            Interp1D(x_src, x_dst)(y_src, None, kind="nearest")

    def test_invalid_kind(self):
        x_src = array([10, 20, 30, 40, 50, 60, 70, 80, 90])
        y_src = array([1, 2, 3, 4, 5, 6, 7, 8, 9])
        x_dst = array(GLOBAL_X_DST)

        with self.assertRaises(ValueError):
            Interp1D(x_src, x_dst)(y_src, None, kind="-= invalid =-")

#-------------------------------------------------------------------------------

class TestI1DNearestScalarEmptyTarget(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_SRC = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    X_DST = []
    Y_DST = []


class TestI1DPreviousScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'previous'


class TestI1DZeroScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'zero'


class TestI1DLinearScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'linear'


class TestI1DFallbackLinearScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'cubic'


class TestI1DCubicScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'cubic'
    DY_DST = []


class TestI1DNearestScalarEmptyTargetWithNeighbourhood(TestI1DNearestScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DPreviousScalarEmptyTargetWithNeighbourhood(TestI1DPreviousScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroScalarEmptyTargetWithNeighbourhood(TestI1DZeroScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearScalarEmptyTargetWithNeighbourhood(TestI1DLinearScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DFallbackLinearScalarEmptyTargetWithNeighbourhood(TestI1DFallbackLinearScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DCubicScalarEmptyTargetWithNeighbourhood(TestI1DCubicScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestVectorEmptyTarget(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_SRC = [
        [1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4],
        [5, 5, 5], [6, 6, 6], [7, 7, 7], [8, 8, 8], [9, 9, 9]
    ]
    X_DST = []
    Y_DST = empty((0, 3))


class TestI1DPreviousVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'previous'


class TestI1DZeroVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'zero'


class TestI1DLinearVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'linear'


class TestI1DFallbackLinearVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'cubic'


class TestI1DCubicVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'cubic'
    DY_SRC = [
        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]
    ]


class TestI1DNearestVectorEmptyTargetWithNeighbourhood(TestI1DNearestVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DPreviousVectorEmptyTargetWithNeighbourhood(TestI1DPreviousVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroVectorEmptyTargetWithNeighbourhood(TestI1DZeroVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearVectorEmptyTargetWithNeighbourhood(TestI1DLinearVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DFallbackLinearVectorEmptyTargetWithNeighbourhood(TestI1DFallbackLinearVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DCubicVectorEmptyTargetWithNeighbourhood(TestI1DCubicVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestScalarEmptySource(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = []
    Y_SRC = []
    X_DST = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_DST = [nan, nan, nan, nan, nan, nan, nan, nan, nan]


class TestI1DPreviousScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'previous'


class TestI1DZeroScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'zero'


class TestI1DLinearScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'linear'


class TestI1DFallbackLinearScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'cubic'


class TestI1DCubicScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'cubic'
    DY_SRC = []


class TestI1DNearestScalarEmptySourceWithNeighbourhood(TestI1DNearestScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DPreviousScalarEmptySourceWithNeighbourhood(TestI1DPreviousScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroScalarEmptySourceWithNeighbourhood(TestI1DZeroScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearScalarEmptySourceWithNeighbourhood(TestI1DLinearScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DFallbackLinearScalarEmptySourceWithNeighbourhood(TestI1DFallbackLinearScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DCubicScalarEmptySourceWithNeighbourhood(TestI1DCubicScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestVectorEmptySource(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = []
    Y_SRC = empty((0, 3))
    X_DST = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_DST = full((9, 3), nan)


class TestI1DPreviousVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'previous'


class TestI1DZeroVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'zero'


class TestI1DLinearVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'linear'


class TestI1DFallbackLinearVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'cubic'


class TestI1DCubicVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'cubic'
    DY_SRC = empty((0, 3))


class TestI1DNearestVectorEmptySourceWithNeighbourhood(TestI1DNearestVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DPreviousVectorEmptySourceWithNeighbourhood(TestI1DPreviousVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroVectorEmptySourceWithNeighbourhood(TestI1DZeroVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearVectorEmptySourceWithNeighbourhood(TestI1DLinearVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DFallbackLinearVectorEmptySourceWithNeighbourhood(TestI1DFallbackLinearVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DCubicVectorEmptySourceWithNeighbourhood(TestI1DCubicVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestScalarNoGap(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_SRC = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 2,
        2, 2, 2, 3,
        3, 3, 3, 4,
        4, 4, 4, 5,
        5, 5, 5, 6,
        6, 6, 6, 7,
        7, 7, 7, 8,
        8, 8, 8, 9,
        9, nan, nan, nan,
    ]


class TestI1DPreviousScalarNoGap(TestI1DNearestScalarNoGap):
    KIND = 'previous'
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, 6, 6, 6,
        7, 7, 7, 7,
        8, 8, 8, 8,
        9, nan, nan, nan,
    ]


class TestI1DZeroScalarNoGap(TestI1DPreviousScalarNoGap):
    KIND = 'zero'


class TestI1DLinearScalarNoGap(TestI1DNearestScalarNoGap):
    KIND = 'linear'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DFallbackLinearScalarNoGap(TestI1DLinearScalarNoGap):
    KIND = 'cubic'


class TestI1DCubicScalarNoGap(TestI1DNearestScalarNoGap):
    KIND = 'cubic'
    DY_SRC = [0, -1, 0, 1, 0, -1, 0, 1, 0]
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.846, 2.75, 3.254,
        2.0, 0.746, 1.25, 2.154,
        3.0, 2.586, 2.25, 2.314,
        4.0, 5.686, 5.75, 5.414,
        5.0, 5.846, 6.75, 7.254,
        6.0, 4.746, 5.25, 6.154,
        7.0, 6.586, 6.25, 6.314,
        8.0, 9.686, 9.75, 9.414,
        9.0, nan, nan, nan,
    ]


class TestI1DNearestScalarNoGapWithNeighbourhood(TestI1DNearestScalarNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 1,
        1, 1, 1, 2,
        2, 2, 2, 3,
        3, 3, 3, 4,
        4, 4, 4, 5,
        5, 5, 5, 6,
        6, 6, 6, 7,
        7, 7, 7, 8,
        8, 8, 8, 9,
        9, 9, nan, nan,
    ]


class TestI1DPreviousScalarNoGapWithNeighbourhood(TestI1DPreviousScalarNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, 6, 6, 6,
        7, 7, 7, 7,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DZeroScalarNoGapWithNeighbourhood(TestI1DZeroScalarNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, 6, 6, 6,
        7, 7, 7, 7,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DLinearScalarNoGapWithNeighbourhood(TestI1DLinearScalarNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DFallbackLinearScalarNoGapWithNeighbourhood(TestI1DFallbackLinearScalarNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DCubicScalarNoGapWithNeighbourhood(TestI1DCubicScalarNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 2.494,
        1.0, 1.846, 2.75, 3.254,
        2.0, 0.746, 1.25, 2.154,
        3.0, 2.586, 2.25, 2.314,
        4.0, 5.686, 5.75, 5.414,
        5.0, 5.846, 6.75, 7.254,
        6.0, 4.746, 5.25, 6.154,
        7.0, 6.586, 6.25, 6.314,
        8.0, 9.686, 9.75, 9.414,
        9.0, 9.846, nan, nan,
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestVectorNoGap(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_SRC = [
        [1, 1, 1], [2, 2, 2], [3, 3, 3],
        [4, 4, 4], [5, 5, 5], [6, 6, 6],
        [7, 7, 7], [8, 8, 8], [9, 9, 9]
    ]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [3, 3, 3],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [4, 4, 4],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [5, 5, 5],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [6, 6, 6],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [7, 7, 7],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [8, 8, 8],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVectorNoGap(TestI1DNearestVectorNoGap):
    KIND = 'previous'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [3, 3, 3],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [4, 4, 4],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [5, 5, 5],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [6, 6, 6],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [7, 7, 7],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVectorNoGap(TestI1DPreviousVectorNoGap):
    KIND = 'zero'


class TestI1DLinearVectorNoGap(TestI1DNearestVectorNoGap):
    KIND = 'linear'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVectorNoGap(TestI1DNearestVectorNoGap):
    KIND = 'cubic'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVectorNoGap(TestI1DNearestVectorNoGap):
    KIND = 'cubic'
    DY_SRC = [
        [0, 1, -1], [1, -1, 0], [-1, 0, 1],
        [0, 1, -1], [1, -1, 0], [-1, 0, 1],
        [0, 1, -1], [1, -1, 0], [-1, 0, 1],
    ]
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [4.316, 0.746, 1.586], [5.0, 1.25, 1.25], [4.884, 2.154, 1.314],
        [3.0, 3.0, 3.0], [1.746, 2.586, 5.316], [2.25, 2.25, 6.0], [3.154, 2.314, 5.884],
        [4.0, 4.0, 4.0], [3.586, 6.316, 2.746], [3.25, 7.0, 3.25], [3.314, 6.884, 4.154],
        [5.0, 5.0, 5.0], [7.316, 3.746, 4.586], [8.0, 4.25, 4.25], [7.884, 5.154, 4.314],
        [6.0, 6.0, 6.0], [4.746, 5.586, 8.316], [5.25, 5.25, 9.0], [6.154, 5.314, 8.884],
        [7.0, 7.0, 7.0], [6.586, 9.316, 5.746], [6.25, 10.0, 6.25], [6.314, 9.884, 7.154],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]




class TestI1DNearestVectorNoGapWithNeighbourhood(TestI1DNearestVectorNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [1, 1, 1],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [3, 3, 3],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [4, 4, 4],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [5, 5, 5],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [6, 6, 6],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [7, 7, 7],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [8, 8, 8],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVectorNoGapWithNeighbourhood(TestI1DPreviousVectorNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [3, 3, 3],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [4, 4, 4],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [5, 5, 5],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [6, 6, 6],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [7, 7, 7],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVectorNoGapWithNeighbourhood(TestI1DZeroVectorNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [3, 3, 3],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [4, 4, 4],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [5, 5, 5],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [6, 6, 6],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [7, 7, 7],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DLinearVectorNoGapWithNeighbourhood(TestI1DLinearVectorNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVectorNoGapWithNeighbourhood(TestI1DFallbackLinearVectorNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVectorNoGapWithNeighbourhood(TestI1DCubicVectorNoGap):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.154, -2.576, 6.394],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [4.316, 0.746, 1.586], [5.0, 1.25, 1.25], [4.884, 2.154, 1.314],
        [3.0, 3.0, 3.0], [1.746, 2.586, 5.316], [2.25, 2.25, 6.0], [3.154, 2.314, 5.884],
        [4.0, 4.0, 4.0], [3.586, 6.316, 2.746], [3.25, 7.0, 3.25], [3.314, 6.884, 4.154],
        [5.0, 5.0, 5.0], [7.316, 3.746, 4.586], [8.0, 4.25, 4.25], [7.884, 5.154, 4.314],
        [6.0, 6.0, 6.0], [4.746, 5.586, 8.316], [5.25, 5.25, 9.0], [6.154, 5.314, 8.884],
        [7.0, 7.0, 7.0], [6.586, 9.316, 5.746], [6.25, 10.0, 6.25], [6.314, 9.884, 7.154],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [4.776, 7.506, 13.746], [nan, nan, nan], [nan, nan, nan],
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestScalar1Gap2Segments(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 60, 70, 80, 90]
    Y_SRC = [1, 2, 3, 4, 6, 7, 8, 9]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 2,
        2, 2, 2, 3,
        3, 3, 3, 4,
        4, nan, nan, nan,
        nan, nan, nan, nan,
        6, 6, 6, 7,
        7, 7, 7, 8,
        8, 8, 8, 9,
        9, nan, nan, nan,
    ]


class TestI1DPreviousScalar1Gap2Segments(TestI1DNearestScalar1Gap2Segments):
    KIND = 'previous'
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, nan, nan, nan,
        nan, nan, nan, nan,
        6, 6, 6, 6,
        7, 7, 7, 7,
        8, 8, 8, 8,
        9, nan, nan, nan,
    ]


class TestI1DZeroScalar1Gap2Segments(TestI1DPreviousScalar1Gap2Segments):
    KIND = 'zero'


class TestI1DLinearScalar1Gap2Segments(TestI1DNearestScalar1Gap2Segments):
    KIND = 'linear'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, nan, nan, nan,
        nan, nan, nan, nan,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DFallbackLinearScalar1Gap2Segments(TestI1DNearestScalar1Gap2Segments):
    KIND = 'cubic'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, nan, nan, nan,
        nan, nan, nan, nan,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DCubicScalar1Gap2Segments(TestI1DNearestScalar1Gap2Segments):
    KIND = 'cubic'
    DY_SRC = [0, -1, 0, 1, -1, 0, 1, 0]
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.846, 2.75, 3.254,
        2.0, 0.746, 1.25, 2.154,
        3.0, 2.586, 2.25, 2.314,
        4.0, nan, nan, nan,
        nan, nan, nan, nan,
        6.0, 4.746, 5.25, 6.154,
        7.0, 6.586, 6.25, 6.314,
        8.0, 9.686, 9.75, 9.414,
        9.0, nan, nan, nan,
    ]


class TestI1DNearestScalar1Gap2SegmentsWithNeighbourhood(TestI1DNearestScalar1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 1,
        1, 1, 1, 2,
        2, 2, 2, 3,
        3, 3, 3, 4,
        4, 4, nan, nan,
        nan, nan, nan, 6,
        6, 6, 6, 7,
        7, 7, 7, 8,
        8, 8, 8, 9,
        9, 9, nan, nan,
    ]


class TestI1DZeroScalar1Gap2SegmentsWithNeighbourhood(TestI1DZeroScalar1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, 4, nan, nan,
        nan, nan, nan, nan,
        6, 6, 6, 6,
        7, 7, 7, 7,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DLinearScalar1Gap2SegmentsWithNeighbourhood(TestI1DLinearScalar1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, 4.3, nan, nan,
        nan, nan, nan, 5.7,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DFallbackLinearScalar1Gap2SegmentsWithNeighbourhood(TestI1DFallbackLinearScalar1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, 2.5, 2.7,
        3.0, 3.3, 3.5, 3.7,
        4.0, 4.3, nan, nan,
        nan, nan, nan, 5.7,
        6.0, 6.3, 6.5, 6.7,
        7.0, 7.3, 7.5, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DCubicScalar1Gap2SegmentsWithNeighbourhood(TestI1DCubicScalar1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 2.494,
        1.0, 1.846, 2.75, 3.254,
        2.0, 0.746, 1.25, 2.154,
        3.0, 2.586, 2.25, 2.314,
        4.0, 8.746, nan, nan,
        nan, nan, nan, 11.394,
        6.0, 4.746, 5.25, 6.154,
        7.0, 6.586, 6.25, 6.314,
        8.0, 9.686, 9.75, 9.414,
        9.0, 9.846, nan, nan,
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestVector1Gap2Segments(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 60, 70, 80, 90]
    Y_SRC = [
        [1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4],
        [6, 6, 6], [7, 7, 7], [8, 8, 8], [9, 9, 9]
    ]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [3, 3, 3],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [4, 4, 4],
        [4, 4, 4], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [7, 7, 7],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [8, 8, 8],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector1Gap2Segments(TestI1DNearestVector1Gap2Segments):
    KIND = 'previous'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [3, 3, 3],
        [4, 4, 4], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [6, 6, 6],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [7, 7, 7],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector1Gap2Segments(TestI1DPreviousVector1Gap2Segments):
    KIND = 'zero'


class TestI1DLinearVector1Gap2Segments(TestI1DNearestVector1Gap2Segments):
    KIND = 'linear'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector1Gap2Segments(TestI1DNearestVector1Gap2Segments):
    KIND = 'cubic'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector1Gap2Segments(TestI1DNearestVector1Gap2Segments):
    KIND = 'cubic'
    DY_SRC = [
        [0, 1, -1], [1, -1, 0], [-1, 0, 1], [0, 1, -1],
        [-1, 0, 1], [0, 1, -1], [1, -1, 0], [-1, 0, 1],
    ]
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [4.316, 0.746, 1.586], [5.0, 1.25, 1.25], [4.884, 2.154, 1.314],
        [3.0, 3.0, 3.0], [1.746, 2.586, 5.316], [2.25, 2.25, 6.0], [3.154, 2.314, 5.884],
        [4.0, 4.0, 4.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6.0, 6.0, 6.0], [4.746, 5.586, 8.316], [5.25, 5.25, 9.0], [6.154, 5.314, 8.884],
        [7.0, 7.0, 7.0], [6.586, 9.316, 5.746], [6.25, 10.0, 6.25], [6.314, 9.884, 7.154],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DNearestVector1Gap2SegmentsWithNeighbourhood(TestI1DNearestVector1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [1, 1, 1],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [3, 3, 3],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [4, 4, 4],
        [4, 4, 4], [4, 4, 4], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [6, 6, 6],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [7, 7, 7],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [8, 8, 8],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector1Gap2SegmentsWithNeighbourhood(TestI1DPreviousVector1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [3, 3, 3],
        [4, 4, 4], [4, 4, 4], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [6, 6, 6],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [7, 7, 7],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector1Gap2SegmentsWithNeighbourhood(TestI1DZeroVector1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2],
        [3, 3, 3], [3, 3, 3], [3, 3, 3], [3, 3, 3],
        [4, 4, 4], [4, 4, 4], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [6, 6, 6], [6, 6, 6], [6, 6, 6], [6, 6, 6],
        [7, 7, 7], [7, 7, 7], [7, 7, 7], [7, 7, 7],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DLinearVector1Gap2SegmentsWithNeighbourhood(TestI1DLinearVector1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector1Gap2SegmentsWithNeighbourhood(TestI1DFallbackLinearVector1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [2.5, 2.5, 2.5], [2.7, 2.7, 2.7],
        [3.0, 3.0, 3.0], [3.3, 3.3, 3.3], [3.5, 3.5, 3.5], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [6.5, 6.5, 6.5], [6.7, 6.7, 6.7],
        [7.0, 7.0, 7.0], [7.3, 7.3, 7.3], [7.5, 7.5, 7.5], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector1Gap2SegmentsWithNeighbourhood(TestI1DCubicVector1Gap2Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.154, -2.576, 6.394],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [4.316, 0.746, 1.586], [5.0, 1.25, 1.25], [4.884, 2.154, 1.314],
        [3.0, 3.0, 3.0], [1.746, 2.586, 5.316], [2.25, 2.25, 6.0], [3.154, 2.314, 5.884],
        [4.0, 4.0, 4.0], [2.506, 8.746, -0.224], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [11.394, 5.154, 2.424],
        [6.0, 6.0, 6.0], [4.746, 5.586, 8.316], [5.25, 5.25, 9.0], [6.154, 5.314, 8.884],
        [7.0, 7.0, 7.0], [6.586, 9.316, 5.746], [6.25, 10.0, 6.25], [6.314, 9.884, 7.154],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [4.776, 7.506, 13.746], [nan, nan, nan], [nan, nan, nan],
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestScalar2Gaps3Segments(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 40, 50, 60, 80, 90]
    Y_SRC = [1, 2, 4, 5, 6, 8, 9]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 2,
        2, nan, nan, nan,
        nan, nan, nan, nan,
        4, 4, 4, 5,
        5, 5, 5, 6,
        6, nan, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 9,
        9, nan, nan, nan,
    ]


class TestI1DPreviousScalar2Gaps3Segments(TestI1DNearestScalar2Gaps3Segments):
    KIND = 'previous'
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, nan, nan, nan,
        nan, nan, nan, nan,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, nan, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 8,
        9, nan, nan, nan,
    ]


class TestI1DZeroScalar2Gaps3Segments(TestI1DPreviousScalar2Gaps3Segments):
    KIND = 'zero'


class TestI1DLinearScalar2Gaps3Segments(TestI1DNearestScalar2Gaps3Segments):
    KIND = 'linear'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, nan, nan, nan,
        nan, nan, nan, nan,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, nan, nan, nan,
        nan, nan, nan, nan,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DFallbackLinearScalar2Gaps3Segments(TestI1DNearestScalar2Gaps3Segments):
    KIND = 'cubic'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, nan, nan, nan,
        nan, nan, nan, nan,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, nan, nan, nan,
        nan, nan, nan, nan,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DCubicScalar2Gaps3Segments(TestI1DNearestScalar2Gaps3Segments):
    KIND = 'cubic'
    DY_SRC = [0, -1, 1, 0, -1, 1, 0]
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.846, 2.75, 3.254,
        2.0, nan, nan, nan,
        nan, nan, nan, nan,
        4.0, 5.686, 5.75, 5.414,
        5.0, 5.846, 6.75, 7.254,
        6.0, nan, nan, nan,
        nan, nan, nan, nan,
        8.0, 9.686, 9.75, 9.414,
        9.0, nan, nan, nan,
    ]


class TestI1DNearestScalar2Gaps3SegmentsWithNeighbourhood(TestI1DNearestScalar2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 1,
        1, 1, 1, 2,
        2, 2, nan, nan,
        nan, nan, nan, 4,
        4, 4, 4, 5,
        5, 5, 5, 6,
        6, 6, nan, nan,
        nan, nan, nan, 8,
        8, 8, 8, 9,
        9, 9, nan, nan,
    ]


class TestI1DPreviousScalar2Gaps3SegmentsWithNeighbourhood(TestI1DPreviousScalar2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, nan, nan,
        nan, nan, nan, nan,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, 6, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DZeroScalar2Gaps3SegmentsWithNeighbourhood(TestI1DZeroScalar2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, nan, nan,
        nan, nan, nan, nan,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, 6, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DLinearScalar2Gaps3SegmentsWithNeighbourhood(TestI1DLinearScalar2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, nan, nan,
        nan, nan, nan, 3.7,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, 6.3, nan, nan,
        nan, nan, nan, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DFallbackLinearScalar2Gaps3SegmentsWithNeighbourhood(TestI1DFallbackLinearScalar2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, nan, nan,
        nan, nan, nan, 3.7,
        4.0, 4.3, 4.5, 4.7,
        5.0, 5.3, 5.5, 5.7,
        6.0, 6.3, nan, nan,
        nan, nan, nan, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DCubicScalar2Gaps3SegmentsWithNeighbourhood(TestI1DCubicScalar2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 2.494,
        1.0, 1.846, 2.75, 3.254,
        2.0, -3.394, nan, nan,
        nan, nan, nan, -0.746,
        4.0, 5.686, 5.75, 5.414,
        5.0, 5.846, 6.75, 7.254,
        6.0, 0.606, nan, nan,
        nan, nan, nan, 3.254,
        8.0, 9.686, 9.75, 9.414,
        9.0, 9.846, nan, nan
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestVector2Gaps3Segments(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 40, 50, 60, 80, 90]
    Y_SRC = [
        [1, 1, 1], [2, 2, 2], [4, 4, 4], [5, 5, 5],
        [6, 6, 6], [8, 8, 8], [9, 9, 9]
    ]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [5, 5, 5],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [6, 6, 6],
        [6, 6, 6], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector2Gaps3Segments(TestI1DNearestVector2Gaps3Segments):
    KIND = 'previous'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [4, 4, 4],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [5, 5, 5],
        [6, 6, 6], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector2Gaps3Segments(TestI1DPreviousVector2Gaps3Segments):
    KIND = 'zero'


class TestI1DLinearVector2Gaps3Segments(TestI1DNearestVector2Gaps3Segments):
    KIND = 'linear'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector2Gaps3Segments(TestI1DNearestVector2Gaps3Segments):
    KIND = 'cubic'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector2Gaps3Segments(TestI1DNearestVector2Gaps3Segments):
    KIND = 'cubic'
    DY_SRC = [
        [0, 1, -1], [1, -1, 0], [0, 1, -1], [1, -1, 0],
        [-1, 0, 1], [1, -1, 0], [-1, 0, 1],
    ]
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4.0, 4.0, 4.0], [3.586, 6.316, 2.746], [3.25, 7.0, 3.25], [3.314, 6.884, 4.154],
        [5.0, 5.0, 5.0], [7.316, 3.746, 4.586], [8.0, 4.25, 4.25], [7.884, 5.154, 4.314],
        [6.0, 6.0, 6.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DNearestVector2Gaps3SegmentsWithNeighbourhood(TestI1DNearestVector2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [1, 1, 1],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [2, 2, 2], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [4, 4, 4],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [5, 5, 5],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [6, 6, 6],
        [6, 6, 6], [6, 6, 6], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [8, 8, 8],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector2Gaps3SegmentsWithNeighbourhood(TestI1DPreviousVector2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [4, 4, 4],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [5, 5, 5],
        [6, 6, 6], [6, 6, 6], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector2Gaps3SegmentsWithNeighbourhood(TestI1DZeroVector2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [4, 4, 4], [4, 4, 4], [4, 4, 4], [4, 4, 4],
        [5, 5, 5], [5, 5, 5], [5, 5, 5], [5, 5, 5],
        [6, 6, 6], [6, 6, 6], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DLinearVector2Gaps3SegmentsWithNeighbourhood(TestI1DLinearVector2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector2Gaps3SegmentsWithNeighbourhood(TestI1DFallbackLinearVector2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [3.7, 3.7, 3.7],
        [4.0, 4.0, 4.0], [4.3, 4.3, 4.3], [4.5, 4.5, 4.5], [4.7, 4.7, 4.7],
        [5.0, 5.0, 5.0], [5.3, 5.3, 5.3], [5.5, 5.5, 5.5], [5.7, 5.7, 5.7],
        [6.0, 6.0, 6.0], [6.3, 6.3, 6.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector2Gaps3SegmentsWithNeighbourhood(TestI1DCubicVector2Gaps3Segments):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.154, -2.576, 6.394],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [6.746, -2.224, 0.506], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [3.154, 0.424, 9.394],
        [4.0, 4.0, 4.0], [3.586, 6.316, 2.746], [3.25, 7.0, 3.25], [3.314, 6.884, 4.154],
        [5.0, 5.0, 5.0], [7.316, 3.746, 4.586], [8.0, 4.25, 4.25], [7.884, 5.154, 4.314],
        [6.0, 6.0, 6.0], [1.776, 4.506, 10.746], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [4.424, 13.394, 7.154],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [4.776, 7.506, 13.746], [nan, nan, nan], [nan, nan, nan],
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestScalar2Gaps3Segments1Single(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 50, 80, 90]
    Y_SRC = [1, 2, 5, 8, 9]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 2,
        2, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        5, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 9,
        9, nan, nan, nan,
    ]


class TestI1DPreviousScalar2Gaps3Segments1Single(TestI1DNearestScalar2Gaps3Segments1Single):
    KIND = 'previous'
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        5, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 8,
        9, nan, nan, nan,
    ]


class TestI1DZeroScalar2Gaps3Segments1Single(TestI1DPreviousScalar2Gaps3Segments1Single):
    KIND = 'zero'


class TestI1DLinearScalar2Gaps3Segments1Single(TestI1DNearestScalar2Gaps3Segments1Single):
    KIND = 'linear'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DFallbackLinearScalar2Gaps3Segments1Single(TestI1DNearestScalar2Gaps3Segments1Single):
    KIND = 'cubic'
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.3, 1.5, 1.7,
        2.0, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8.0, 8.3, 8.5, 8.7,
        9.0, nan, nan, nan,
    ]


class TestI1DCubicScalar2Gaps3Segments1Single(TestI1DNearestScalar2Gaps3Segments1Single):
    KIND = 'cubic'
    DY_SRC = [0, -1, 0, 1, 0]
    Y_DST = [
        nan, nan, nan, nan,
        1.0, 1.846, 2.75, 3.254,
        2.0, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8.0, 9.686, 9.75, 9.414,
        9.0, nan, nan, nan,
    ]


class TestI1DNearestScalar2Gaps3Segments1SingleWithNeighbourhood(TestI1DNearestScalar2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 1,
        1, 1, 1, 2,
        2, 2, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, 5,
        5, 5, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, 8,
        8, 8, 8, 9,
        9, 9, nan, nan,
    ]


class TestI1DPreviousScalar2Gaps3Segments1SingleWithNeighbourhood(TestI1DPreviousScalar2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        5, 5, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DZeroScalar2Gaps3Segments1SingleWithNeighbourhood(TestI1DZeroScalar2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, 1, 1,
        2, 2, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        5, 5, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        8, 8, 8, 8,
        9, 9, nan, nan,
    ]


class TestI1DLinearScalar2Gaps3Segments1SingleWithNeighbourhood(TestI1DLinearScalar2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DFallbackLinearScalar2Gaps3Segments1SingleWithNeighbourhood(TestI1DFallbackLinearScalar2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 0.7,
        1.0, 1.3, 1.5, 1.7,
        2.0, 2.3, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, 7.7,
        8.0, 8.3, 8.5, 8.7,
        9.0, 9.3, nan, nan,
    ]


class TestI1DCubicScalar2Gaps3Segments1SingleWithNeighbourhood(TestI1DCubicScalar2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 2.494,
        1.0, 1.846, 2.75, 3.254,
        2.0, -3.394, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, 3.254,
        8.0, 9.686, 9.75, 9.414,
        9.0, 9.846, nan, nan
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestVector2Gaps3Segments1Single(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 50, 80, 90]
    Y_SRC = [[1, 1, 1], [2, 2, 2], [5, 5, 5], [8, 8, 8], [9, 9, 9]]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector2Gaps3Segments1Single(TestI1DNearestVector2Gaps3Segments1Single):
    KIND = 'previous'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector2Gaps3Segments1Single(TestI1DPreviousVector2Gaps3Segments1Single):
    KIND = 'zero'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DLinearVector2Gaps3Segments1Single(TestI1DNearestVector2Gaps3Segments1Single):
    KIND = 'linear'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector2Gaps3Segments1Single(TestI1DNearestVector2Gaps3Segments1Single):
    KIND = 'cubic'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector2Gaps3Segments1Single(TestI1DNearestVector2Gaps3Segments1Single):
    KIND = 'cubic'
    DY_SRC = [[0, 1, -1], [1, -1, 0], [1, -1, 0], [1, -1, 0], [-1, 0, 1]]
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DNearestVector2Gaps3Segments1SingleWithNeighbourhood(TestI1DNearestVector2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [1, 1, 1],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [2, 2, 2],
        [2, 2, 2], [2, 2, 2], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [5, 5, 5],
        [5, 5, 5], [5, 5, 5], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [8, 8, 8],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [9, 9, 9],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector2Gaps3Segments1SingleWithNeighbourhood(TestI1DPreviousVector2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [5, 5, 5], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector2Gaps3Segments1SingleWithNeighbourhood(TestI1DZeroVector2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1],
        [2, 2, 2], [2, 2, 2], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [5, 5, 5], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DLinearVector2Gaps3Segments1SingleWithNeighbourhood(TestI1DLinearVector2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector2Gaps3Segments1SingleWithNeighbourhood(TestI1DFallbackLinearVector2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.7, 0.7, 0.7],
        [1.0, 1.0, 1.0], [1.3, 1.3, 1.3], [1.5, 1.5, 1.5], [1.7, 1.7, 1.7],
        [2.0, 2.0, 2.0], [2.3, 2.3, 2.3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [7.7, 7.7, 7.7],
        [8.0, 8.0, 8.0], [8.3, 8.3, 8.3], [8.5, 8.5, 8.5], [8.7, 8.7, 8.7],
        [9.0, 9.0, 9.0], [9.3, 9.3, 9.3], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector2Gaps3Segments1SingleWithNeighbourhood(TestI1DCubicVector2Gaps3Segments1Single):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [0.154, -2.576, 6.394],
        [1.0, 1.0, 1.0], [0.586, 3.316, -0.254], [0.25, 4.0, 0.25], [0.314, 3.884, 1.154],
        [2.0, 2.0, 2.0], [6.746, -2.224, 0.506], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [4.424, 13.394, 7.154],
        [8.0, 8.0, 8.0], [10.316, 6.746, 7.586], [11.0, 7.25, 7.25], [10.884, 8.154, 7.314],
        [9.0, 9.0, 9.0], [4.776, 7.506, 13.746], [nan, nan, nan], [nan, nan, nan],
    ]

#-------------------------------------------------------------------------------

class TestI1DNearestScalar4Gaps5Segments5Singles(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 30, 50, 70, 90]
    Y_SRC = [1, 3, 5, 7, 9]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        nan, nan, nan, nan,
        1, nan, nan, nan,
        nan, nan, nan, nan,
        3, nan, nan, nan,
        nan, nan, nan, nan,
        5, nan, nan, nan,
        nan, nan, nan, nan,
        7, nan, nan, nan,
        nan, nan, nan, nan,
        9, nan, nan, nan,
    ]


class TestI1DPreviousScalar4Gaps5Segments5Singles(TestI1DNearestScalar4Gaps5Segments5Singles):
    KIND = 'previous'


class TestI1DZeroScalar4Gaps5Segments5Singles(TestI1DPreviousScalar4Gaps5Segments5Singles):
    KIND = 'zero'


class TestI1DLinearScalar4Gaps5Segments5Singles(TestI1DNearestScalar4Gaps5Segments5Singles):
    KIND = 'linear'
    Y_DST = [
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
    ]


class TestI1DFallbackLinearScalar4Gaps5Segments5Singles(TestI1DNearestScalar4Gaps5Segments5Singles):
    KIND = 'cubic'
    Y_DST = [
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
    ]


class TestI1DCubicScalar4Gaps5Segments5Singles(TestI1DNearestScalar4Gaps5Segments5Singles):
    KIND = 'cubic'
    DY_SRC = [0, 0, 0, 0, 0]
    Y_DST = [
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
        nan, nan, nan, nan,
    ]


class TestI1DNearestScalar4Gaps5Segments5SinglesWithNeighbourhood(TestI1DNearestScalar4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, 1,
        1, 1, nan, nan,
        nan, nan, nan, 3,
        3, 3, nan, nan,
        nan, nan, nan, 5,
        5, 5, nan, nan,
        nan, nan, nan, 7,
        7, 7, nan, nan,
        nan, nan, nan, 9,
        9, 9, nan, nan,
    ]


class TestI1DPreviousScalar4Gaps5Segments5SinglesWithNeighbourhood(TestI1DPreviousScalar4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, nan, nan,
        nan, nan, nan, nan,
        3, 3, nan, nan,
        nan, nan, nan, nan,
        5, 5, nan, nan,
        nan, nan, nan, nan,
        7, 7, nan, nan,
        nan, nan, nan, nan,
        9, 9, nan, nan,
    ]


class TestI1DZeroScalar4Gaps5Segments5SinglesWithNeighbourhood(TestI1DZeroScalar4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        nan, nan, nan, nan,
        1, 1, nan, nan,
        nan, nan, nan, nan,
        3, 3, nan, nan,
        nan, nan, nan, nan,
        5, 5, nan, nan,
        nan, nan, nan, nan,
        7, 7, nan, nan,
        nan, nan, nan, nan,
        9, 9, nan, nan,
    ]


class TestI1DLinearScalar4Gaps5Segments5SinglesWithNeighbourhood(TestI1DLinearScalar4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DFallbackLinearScalar4Gaps5Segments5SinglesWithNeighbourhood(TestI1DFallbackLinearScalar4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DCubicScalar4Gaps5Segments5SinglesWithNeighbourhood(TestI1DCubicScalar4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestVector4Gaps5Segments5Singles(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 30, 50, 70, 90]
    Y_SRC = [[1, 1, 1], [3, 3, 3], [5, 5, 5], [7, 7, 7], [9, 9, 9]]
    X_DST = GLOBAL_X_DST
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [3, 3, 3], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [7, 7, 7], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [9, 9, 9], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector4Gaps5Segments5Singles(TestI1DNearestVector4Gaps5Segments5Singles):
    KIND = 'previous'


class TestI1DZeroVector4Gaps5Segments5Singles(TestI1DNearestVector4Gaps5Segments5Singles):
    KIND = 'zero'


class TestI1DLinearVector4Gaps5Segments5Singles(TestI1DNearestVector4Gaps5Segments5Singles):
    KIND = 'linear'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DFallbackLinearVector4Gaps5Segments5Singles(TestI1DNearestVector4Gaps5Segments5Singles):
    KIND = 'cubic'
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DCubicVector4Gaps5Segments5Singles(TestI1DNearestVector4Gaps5Segments5Singles):
    KIND = 'cubic'
    DY_SRC = [[0, 1, -1], [-1, 0, 1], [1, -1, 0], [0, 1, -1], [-1, 0, 1]]
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DNearestVector4Gaps5Segments5SinglesWithNeighbourhood(TestI1DNearestVector4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [1, 1, 1],
        [1, 1, 1], [1, 1, 1], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [3, 3, 3],
        [3, 3, 3], [3, 3, 3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [5, 5, 5],
        [5, 5, 5], [5, 5, 5], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [7, 7, 7],
        [7, 7, 7], [7, 7, 7], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [9, 9, 9],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DPreviousVector4Gaps5Segments5SinglesWithNeighbourhood(TestI1DPreviousVector4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [3, 3, 3], [3, 3, 3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [5, 5, 5], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [7, 7, 7], [7, 7, 7], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DZeroVector4Gaps5Segments5SinglesWithNeighbourhood(TestI1DZeroVector4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4
    Y_DST = [
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [1, 1, 1], [1, 1, 1], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [3, 3, 3], [3, 3, 3], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [5, 5, 5], [5, 5, 5], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [7, 7, 7], [7, 7, 7], [nan, nan, nan], [nan, nan, nan],
        [nan, nan, nan], [nan, nan, nan], [nan, nan, nan], [nan, nan, nan],
        [9, 9, 9], [9, 9, 9], [nan, nan, nan], [nan, nan, nan],
    ]


class TestI1DLinearVector4Gaps5Segments5SinglesWithNeighbourhood(TestI1DLinearVector4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DFallbackLinearVector4Gaps5Segments5SinglesWithNeighbourhood(TestI1DFallbackLinearVector4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DCubicVector4Gaps5Segments5SinglesWithNeighbourhood(TestI1DCubicVector4Gaps5Segments5Singles):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
