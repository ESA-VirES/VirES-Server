#-------------------------------------------------------------------------------
#
#  Calculation of finite differences approximation of first derivatives.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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
# pylint: disable=missing-docstring, too-many-arguments

from unittest import main, TestCase
from numpy import asarray, nan, inf
from vires.tests import ArrayMixIn
from vires.finite_differences import (
    get_slopes_from_nodes,
    generate_contiguous_ranges,
)



class TestDataset(ArrayMixIn, TestCase):
    X = asarray([1, 2, 3, 4, 6, 8, 9, 10, 11])
    Y = 0.5 * X**2

    def _test_generate_contiguous_ranges(self, input_, expected_output,
                                         gap_threshold=inf):
        self.assertEqual(
            list(generate_contiguous_ranges(
                asarray(input_), gap_threshold=gap_threshold
            )),
            expected_output
        )

    def _test_get_slopes_from_nodes(self, x_input, y_input, expected_output,
                                    fill_border_values=False, gap_threshold=inf):
        self.assertAllEqual(
            get_slopes_from_nodes(
                asarray(x_input), asarray(y_input),
                fill_border_values=fill_border_values,
                gap_threshold=gap_threshold
            ),
            asarray(expected_output)
        )

    def test_slopes_from_nodes_empty(self):
        self._test_get_slopes_from_nodes([], [], [])

    def test_slopes_from_nodes_1_element(self):
        self._test_get_slopes_from_nodes([1], [1], [nan])

    def test_slopes_from_nodes_2_elements(self):
        self._test_get_slopes_from_nodes([1, 2], [1, 1], [nan, nan])

    def test_slopes_from_nodes_2_elements_with_border(self):
        self._test_get_slopes_from_nodes(
            [1, 2], [1, 1], [0, 0],
            fill_border_values=True
        )

    def test_slopes_from_nodes_3_elements(self):
        self._test_get_slopes_from_nodes([1, 2, 3], [1, 2, 1], [nan, 0, nan])

    def test_slopes_from_nodes_3_elements_with_border(self):
        self._test_get_slopes_from_nodes(
            [1, 2, 3], [1, 2, 1], [1, 0, -1],
            fill_border_values=True
        )

    def test_slopes_from_nodes_nogap(self):
        self._test_get_slopes_from_nodes(
            self.X, self.Y, [nan, 2, 3, 4, 6, 8, 9, 10, nan],
        )

    def test_slopes_from_nodes_nogap_with_border(self):
        self._test_get_slopes_from_nodes(
            self.X, self.Y, [1.5, 2, 3, 4, 6, 8, 9, 10, 10.5],
            fill_border_values=True
        )

    def test_slopes_from_nodes_with_gaps(self):
        self._test_get_slopes_from_nodes(
            self.X, self.Y, [nan, 2, 3, nan, nan, nan, 9, 10, nan],
            gap_threshold=1,
        )

    def test_slopes_from_nodes_nogap_with_gaps_and_border(self):
        self._test_get_slopes_from_nodes(
            self.X, self.Y, [1.5, 2, 3, 3.5, nan, 8.5, 9, 10, 10.5],
            gap_threshold=1,
            fill_border_values=True
        )

    def test_contiguous_ranges_empty(self):
        self._test_generate_contiguous_ranges([], [])

    def test_contiguous_ranges_nogap(self):
        self._test_generate_contiguous_ranges(
            self.X, [(0, 9)],
        )

    def test_contiguous_ranges_with_gaps(self):
        self._test_generate_contiguous_ranges(
            self.X, [(0, 4), (4, 5), (5, 9)], gap_threshold=1,
        )


if __name__ == "__main__":
    main()
