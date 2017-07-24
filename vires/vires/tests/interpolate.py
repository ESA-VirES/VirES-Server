#-------------------------------------------------------------------------------
#
#  Testing gap-aware 1D interpolation.
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
from logging import getLogger, DEBUG, INFO, Formatter, StreamHandler
from numpy import array, nan
from vires.tests import ArrayMixIn
from vires.interpolate import Interp1D

LOG_LEVEL = INFO

def set_stream_handler(logger, level=DEBUG):
    """ Set stream handler to the logger. """
    formatter = Formatter('%(levelname)s: %(module)s: %(message)s')
    handler = StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(min(level, logger.level))

set_stream_handler(getLogger(), LOG_LEVEL)


class TestUtil(ArrayMixIn, unittest.TestCase):

    def test_1d_interp(self):
        gap_threshold = 10

        def test(x_src, x_dst, y_src, y_dst,
                 segment_neighbourhood=0, kind='nearest'):
            result = Interp1D(
                x_src, x_dst, gap_threshold, segment_neighbourhood
            )(y_src, kind)
            try:
                self.assertAllEqual(result, y_dst)
            except:
                print "x_src:", x_src
                print "x_dst:", x_dst
                print "y_src:", y_src
                print "expected:", y_dst
                print "received:", result
                raise

        x_dst = array([
            0, 3, 5, 7,
            10, 13, 15, 17, 20, 23, 25, 27, 30, 33, 35, 37,
            40, 43, 45, 47, 50, 53, 55, 57, 60, 63, 65, 67,
            70, 73, 75, 77, 80, 83, 85, 87, 90, 93, 95, 97,
        ])

        # no gap
        test(
            array([10, 20, 30, 40, 50, 60, 70, 80, 90]), x_dst,
            array([1, 2, 3, 4, 5, 6, 7, 8, 9]),
            array([
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
            ]),
        )

        # 1 gap - 2 segments
        test(
            array([10, 20, 30, 40, 60, 70, 80, 90]), x_dst,
            array([1, 2, 3, 4, 6, 7, 8, 9]),
            array([
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
            ]),
        )

        # 2 gaps - 3 segments
        test(
            array([10, 20, 40, 50, 60, 80, 90]), x_dst,
            array([1, 2, 4, 5, 6, 8, 9]),
            array([
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
            ]),
        )

        # 2 gaps - 3 segments - 1 zero-length segment
        test(
            array([10, 20, 50, 80, 90]), x_dst,
            array([1, 2, 5, 8, 9]),
            array([
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
            ]),
        )

        # 4 gaps - 5 segments - 5 zero-length segment
        test(
            array([10, 30, 50, 70, 90]), x_dst,
            array([1, 3, 5, 7, 9]),
            array([
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
            ]),
        )

        # no gap + neighbourhood
        test(
            array([10, 20, 30, 40, 50, 60, 70, 80, 90]), x_dst,
            array([1, 2, 3, 4, 5, 6, 7, 8, 9]),
            array([
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
            ]),
            segment_neighbourhood=4,
        )

        # 1 gap - 2 segments + neighbourhood
        test(
            array([10, 20, 30, 40, 60, 70, 80, 90]), x_dst,
            array([1, 2, 3, 4, 6, 7, 8, 9]),
            array([
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
            ]),
            segment_neighbourhood=4,
        )

        # 2 gaps - 3 segments + neighbourhood
        test(
            array([10, 20, 40, 50, 60, 80, 90]), x_dst,
            array([1, 2, 4, 5, 6, 8, 9]),
            array([
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
            ]),
            segment_neighbourhood=4,
        )

        # 2 gaps - 3 segments - 1 zero-length segment + neighbourhood
        test(
            array([10, 20, 50, 80, 90]), x_dst,
            array([1, 2, 5, 8, 9]),
            array([
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
            ]),
            segment_neighbourhood=4,
        )

        # 4 gaps - 5 segments - 5 zero-length segment + neighbourhood
        test(
            array([10, 30, 50, 70, 90]), x_dst,
            array([1, 3, 5, 7, 9]),
            array([
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
            ]),
            segment_neighbourhood=4,
        )


if __name__ == "__main__":
    unittest.main()
