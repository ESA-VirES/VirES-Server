#-------------------------------------------------------------------------------
#
# Orbit direction - merge tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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

from unittest import TestCase, main
from collections import namedtuple
from vires.orbit_direction.merge import resolve_overlaps


class TestSegment(namedtuple("TestSegment", ["id", "start", "end"])):
    """ Test segment class. """

    def trim(self, start, end):
        """ Trim the time extent. """
        return self.__class__(
            self.id, max(start, self.start), min(end, self.end)
        )


class TestSegmentOverlapResolved(TestCase):

    @staticmethod
    def _resolve_overlaps(sources):
        return resolve_overlaps([
            [TestSegment(*item) for item in source]
            for source in sources
        ])

    def _test_merge(self, inputs, expected):
        self.assertEqual(self._resolve_overlaps(inputs), expected)

    def test_empty(self):
        self._test_merge([], [])

    def test_single(self):
        self._test_merge([[("A", 1, 2)]], [("A", 1, 2)])

    def test_no_overlap_same_source(self):
        self._test_merge(
            [[("A", 1, 2), ("B", 3, 4)]],
            [("A", 1, 2), ("B", 3, 4)]
        )

    def test_no_overlap_mixed_sources_1(self):
        self._test_merge(
            [[("A", 1, 2)], [("B", 3, 4)]],
            [("A", 1, 2), ("B", 3, 4)]
        )

    def test_no_overlap_mixed_sources_2(self):
        self._test_merge(
            [[("B", 3, 4)], [("A", 1, 2)]],
            [("A", 1, 2), ("B", 3, 4)]
        )

    def test_no_overlap_adjectent_1(self):
        self._test_merge(
            [[("A", 1, 2)], [("B", 2, 3)]],
            [("A", 1, 2), ("B", 2, 3)]
        )

    def test_no_overlap_adjecent_2(self):
        self._test_merge(
            [[("B", 2, 3)], [("A", 1, 2)]],
            [("A", 1, 2), ("B", 2, 3)]
        )

    def test_overlapped_complete_cover(self):
        self._test_merge(
            [[("A", 1, 4)], [("B", 2, 3)]],
            [("A", 1, 4)]
        )

    def test_overlapped_head_tail(self):
        self._test_merge(
            [[("A", 2, 3)], [("B", 1, 4)]],
            [("B", 1, 2), ("A", 2, 3), ("B", 3, 4)]
        )

    def test_overlapped_tail(self):
        self._test_merge(
            [[("A", 1, 3)], [("B", 2, 4)]],
            [("A", 1, 3), ("B", 3, 4)]
        )

    def test_overlapped_head(self):
        self._test_merge(
            [[("A", 2, 4)], [("B", 1, 3)]],
            [("B", 1, 2), ("A", 2, 4)]
        )

    def test_overlapped_multilevel(self):
        self._test_merge(
            [
                [("A", 3, 4), ("B", 7, 8)],
                [("C", 2, 6)],
                [("D", 1, 4), ("E", 5, 9)],
            ],
            [
                ("D", 1, 2), ("C", 2, 3), ("A", 3, 4), ("C", 4, 6),
                ("E", 6, 7), ("B", 7, 8), ("E", 8, 9),
            ]
        )


if __name__ == "__main__":
    main()
