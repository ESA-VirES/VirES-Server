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
    X_DST = None
    Y_DST = None

    def test_interp1d(self):
        x_src = array(self.X_SRC)
        y_src = array(self.Y_SRC)
        x_dst = array(self.X_DST)
        y_dst = array(self.Y_DST)
        result = Interp1D(
            x_src, x_dst, self.GAP_THRESHOLD,
            self.SEGMENT_NEIGHBOURHOOD
        )(y_src, self.KIND)
        try:
            assert_allclose(result, self.Y_DST, atol=1e-12)
        except:
            print()
            print(self.__class__.__name__)
            print("x_src:", x_src)
            print("x_dst:", x_dst)
            print("y_src:", y_src)
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
            Interp1D(x_src, x_dst)(y_src, "nearest")

    def test_invalid_kind(self):
        x_src = array([10, 20, 30, 40, 50, 60, 70, 80, 90])
        y_src = array([1, 2, 3, 4, 5, 6, 7, 8, 9])
        x_dst = array(GLOBAL_X_DST)

        with self.assertRaises(ValueError):
            Interp1D(x_src, x_dst)(y_src, "-= invalid =-")

#-------------------------------------------------------------------------------

class TestI1DNearestScalarEmptyTarget(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_SRC = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    X_DST = []
    Y_DST = []


class TestI1DZeroScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'zero'


class TestI1DLinearScalarEmptyTarget(TestI1DNearestScalarEmptyTarget):
    KIND = 'linear'


class TestI1DNearestScalarEmptyTargetWithNeighbourhood(TestI1DNearestScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroScalarEmptyTargetWithNeighbourhood(TestI1DZeroScalarEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearScalarEmptyTargetWithNeighbourhood(TestI1DLinearScalarEmptyTarget):
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


class TestI1DZeroVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'zero'


class TestI1DLinearVectorEmptyTarget(TestI1DNearestVectorEmptyTarget):
    KIND = 'linear'


class TestI1DNearestVectorEmptyTargetWithNeighbourhood(TestI1DNearestVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroVectorEmptyTargetWithNeighbourhood(TestI1DZeroVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearVectorEmptyTargetWithNeighbourhood(TestI1DLinearVectorEmptyTarget):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestScalarEmptySource(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = []
    Y_SRC = []
    X_DST = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_DST = [nan, nan, nan, nan, nan, nan, nan, nan, nan]


class TestI1DZeroScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'zero'


class TestI1DLinearScalarEmptySource(TestI1DNearestScalarEmptySource):
    KIND = 'linear'


class TestI1DNearestScalarEmptySourceWithNeighbourhood(TestI1DNearestScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroScalarEmptySourceWithNeighbourhood(TestI1DZeroScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearScalarEmptySourceWithNeighbourhood(TestI1DLinearScalarEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4

#-------------------------------------------------------------------------------

class TestI1DNearestVectorEmptySource(InterplateTestMixIn, TestCase):
    KIND = 'nearest'
    X_SRC = []
    Y_SRC = empty((0, 3))
    X_DST = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    Y_DST = full((9, 3), nan)


class TestI1DZeroVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'zero'


class TestI1DLinearVectorEmptySource(TestI1DNearestVectorEmptySource):
    KIND = 'linear'


class TestI1DNearestVectorEmptySourceWithNeighbourhood(TestI1DNearestVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DZeroVectorEmptySourceWithNeighbourhood(TestI1DZeroVectorEmptySource):
    SEGMENT_NEIGHBOURHOOD = 4


class TestI1DLinearVectorEmptySourceWithNeighbourhood(TestI1DLinearVectorEmptySource):
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


class TestI1DZeroScalarNoGap(TestI1DNearestScalarNoGap):
    KIND = 'zero'
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


class TestI1DZeroVectorNoGap(TestI1DNearestVectorNoGap):
    KIND = 'zero'
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


class TestI1DZeroScalar1Gap2Segments(TestI1DNearestScalar1Gap2Segments):
    KIND = 'zero'
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


class TestI1DZeroVector1Gap2Segments(TestI1DNearestVector1Gap2Segments):
    KIND = 'zero'
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


class TestI1DZeroScalar2Gaps3Segments(TestI1DNearestScalar2Gaps3Segments):
    KIND = 'zero'
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


class TestI1DZeroVector2Gaps3Segments(TestI1DNearestVector2Gaps3Segments):
    KIND = 'zero'
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


class TestI1DZeroScalar2Gaps3Segments1Single(TestI1DNearestScalar2Gaps3Segments1Single):
    KIND = 'zero'
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


class TestI1DZeroVector2Gaps3Segments1Single(TestI1DNearestVector2Gaps3Segments1Single):
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


class TestI1DZeroScalar4Gaps5Segments5Singles(TestI1DNearestScalar4Gaps5Segments5Singles):
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

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
