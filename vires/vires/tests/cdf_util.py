#-------------------------------------------------------------------------------
#
# Testing Auxiliary Data Handling
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

# TODO: Test cdf_time_interp .
import unittest
from StringIO import StringIO

from vires.cdf_util import (
    cdf_open, cdf_time_subset, cdf_time_interp,
    cdf_rawtime2mjd2000,
)
from vires.aux import parse_dst
from vires.tests.aux import TEST_DST, DATA_DST, ArrayMixIn

class TestCDF(ArrayMixIn, unittest.TestCase):
    FILE = "./test_tmp_cdf.cdf"

    def setUp(self):
        with cdf_open(self.FILE, "w") as cdf:
            cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
                parse_dst(StringIO(TEST_DST))
            )

    def _cdf_time_subset(self, fields, start, stop, idx_start, idx_stop, margin=0):
        """ Testing CDF read. """
        with cdf_open(self.FILE) as cdf:
            for field, value in cdf_time_subset(cdf, start, stop, fields, margin):
                self.assertEqual(value.shape, (idx_stop - idx_start,))
                self.assertAllEqual(value, cdf[field][idx_start:idx_stop])
                self.assertAllEqual(value, DATA_DST[field][idx_start:idx_stop])

    def test_cdf_time_subset_margin1(self):
        # full interval
        self._cdf_time_subset(('time', 'dst'), -729.97917, -728.56250, 0, 35, 1)
        self._cdf_time_subset(('time', 'dst'), -731.00, -728.00, 0, 35, 1)
        self._cdf_time_subset(('time', 'dst'), -729.97, -728.57, 0, 35, 1)
        # inner subset
        self._cdf_time_subset(('time', 'dst'), -729.60, -729.00, 9, 25, 1)
        # partial overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -729.00, 0, 25, 1)
        # partial overlap - upper
        self._cdf_time_subset(('time', 'dst'), -729.60, -725.00, 9, 35, 1)
        # no overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -730.00, 0, 0, 1)
        self._cdf_time_subset(('time', 'dst'), -733.00, -732.00, 0, 0, 1)
        # no overlap - upper
        self._cdf_time_subset(('time', 'dst'), -728.54, -725.00, 0, 0, 1)
        self._cdf_time_subset(('time', 'dst'), -724.00, -725.00, 0, 0, 1)

    def test_cdf_time_subset(self):
        # full interval
        self._cdf_time_subset(('time', 'dst'), -729.97917, -728.56250, 0, 35)
        self._cdf_time_subset(('time', 'dst'), -731.00, -728.00, 0, 35)
        # inner subset
        self._cdf_time_subset(('time', 'dst'), -729.60, -729.00, 10, 24)
        # partial overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -729.00, 0, 24)
        # partial overlap - upper
        self._cdf_time_subset(('time', 'dst'), -729.60, -725.00, 10, 35)
        # no overlap - lower
        self._cdf_time_subset(('time', 'dst'), -733.00, -730.00, 0, 0)
        self._cdf_time_subset(('time', 'dst'), -733.00, -732.00, 0, 0)
        # no overlap - upper
        self._cdf_time_subset(('time', 'dst'), -728.54, -725.00, 0, 0)
        self._cdf_time_subset(('time', 'dst'), -724.00, -725.00, 0, 0)


if __name__ == "__main__":
    unittest.main()
