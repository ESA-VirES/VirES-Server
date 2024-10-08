#-------------------------------------------------------------------------------
#
# Testing Auxiliary Data Handling
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
# pylint: disable=missing-docstring, invalid-name, too-many-arguments

from unittest import TestCase, main
from os import remove
from os.path import exists
from io import StringIO
from numpy import arange, linspace, isnan, logical_not
from scipy.interpolate import interp1d
from vires.tests import ArrayMixIn
from vires.cdf_util import cdf_open, get_cdf_data_reader
from vires.aux_common import array_slice, subset_time, interpolate_time
from vires.aux_dst import parse_dst
from vires.tests.aux_dst import TEST_DST, DATA_DST


class TestCDF(ArrayMixIn, TestCase):
    FILE = "./test_tmp_cdf.cdf"

    def setUp(self):
        with cdf_open(self.FILE, "w") as cdf:
            cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
                parse_dst(StringIO(TEST_DST))
            )

    def tearDown(self):
        if exists(self.FILE):
            remove(self.FILE)

    def _cdf_time_subset(self, fields, start, stop, idx_start, idx_stop, margin=0):
        """ Testing CDF read. """
        with cdf_open(self.FILE) as cdf:
            data = subset_time(
                source=get_cdf_data_reader(cdf),
                start=start,
                stop=stop,
                time_field="time",
                fields=fields,
                margin=margin,
            )
            for field, value in data.items():
                self.assertEqual(value.shape, (idx_stop - idx_start,))
                self.assertAllEqual(value, cdf[field][idx_start:idx_stop])
                self.assertAllEqual(value, DATA_DST[field][idx_start:idx_stop])

    def _cdf_time_interp(self, start, stop, count, **kwargs):
        time = linspace(start, stop, count)
        with cdf_open(self.FILE) as cdf:
            data = interpolate_time(
                source=get_cdf_data_reader(cdf),
                time=time,
                time_field="time",
                fields=("dst",),
                **kwargs
            )

        values = interp1d(
            DATA_DST['time'], DATA_DST['dst'], bounds_error=False, **kwargs
        )(time)

        self.assertEqual(data['dst'].shape, (count,))
        self.assertEqual(isnan(data['dst']).shape, isnan(values).shape)
        self.assertAllAlmostEqual(
            data['dst'][logical_not(isnan(values))],
            values[logical_not(isnan(values))], delta=1e-9
        )

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

    def test_cdf_time_interp(self):
        # full overlap
        self._cdf_time_interp(-732.00, -728.00, 80)
        self._cdf_time_interp(-732.00, -728.00, 80, kind="nearest")
        self._cdf_time_interp(-732.00, -728.00, 80, kind="zero")
        self._cdf_time_interp(-732.00, -728.00, 80, kind="previous")
        # touching the bounds
        self._cdf_time_interp(-728.56251, -728.00, 5)
        self._cdf_time_interp(-728.56251, -728.00, 5, kind="nearest")
        self._cdf_time_interp(-728.56251, -728.00, 5, kind="zero")
        self._cdf_time_interp(-728.56251, -728.00, 5, kind="previous")
        self._cdf_time_interp(-732.00, -729.979169, 5)
        self._cdf_time_interp(-732.00, -729.979169, 5, kind="nearest")
        self._cdf_time_interp(-732.00, -729.979169, 5, kind="zero")
        self._cdf_time_interp(-732.00, -729.979169, 5, kind="previous")
        # out of bounds
        self._cdf_time_interp(-728.00, -726.00, 5)
        self._cdf_time_interp(-728.00, -726.00, 5, kind="nearest")
        self._cdf_time_interp(-728.00, -726.00, 5, kind="zero")
        self._cdf_time_interp(-728.00, -726.00, 5, kind="previous")
        self._cdf_time_interp(-734.00, -732.00, 5)
        self._cdf_time_interp(-734.00, -732.00, 5, kind="nearest")
        self._cdf_time_interp(-734.00, -732.00, 5, kind="zero")
        self._cdf_time_interp(-734.00, -732.00, 5, kind="previous")
        # single value
        self._cdf_time_interp(-729.00, -729.00, 1)
        self._cdf_time_interp(-729.00, -729.00, 1, kind="nearest")
        self._cdf_time_interp(-729.00, -729.00, 1, kind="zero")
        self._cdf_time_interp(-729.00, -729.00, 1, kind="previous")

    def test_array_slice_equidistant(self):
        test_array = arange(11, dtype='float')
        self.assertEqual(array_slice(test_array, -1, 11, 0), slice(0, 11))
        self.assertEqual(array_slice(test_array, -1, 5, 0), slice(0, 6))
        self.assertEqual(array_slice(test_array, -1, 4.5, 0), slice(0, 5))
        self.assertEqual(array_slice(test_array, 5, 11, 0), slice(5, 11))
        self.assertEqual(array_slice(test_array, 5.5, 11, 0), slice(6, 11))
        self.assertEqual(array_slice(test_array, 5, 5, 0), slice(5, 6))
        self.assertEqual(array_slice(test_array, 4.5, 5.5, 0), slice(5, 6))
        self.assertEqual(array_slice(test_array, 4.5, 4.5, 0), slice(5, 5))
        self.assertEqual(array_slice(test_array, 2.5, 7.5, 0), slice(3, 8))

        self.assertEqual(array_slice(test_array, -1, 11, 1), slice(0, 11))
        self.assertEqual(array_slice(test_array, -1, 5, 1), slice(0, 7))
        self.assertEqual(array_slice(test_array, -1, 4.5, 1), slice(0, 6))
        self.assertEqual(array_slice(test_array, 5, 11, 1), slice(4, 11))
        self.assertEqual(array_slice(test_array, 5.5, 11, 1), slice(5, 11))
        self.assertEqual(array_slice(test_array, 5, 5, 1), slice(4, 7))
        self.assertEqual(array_slice(test_array, 4.5, 5.5, 1), slice(4, 7))
        self.assertEqual(array_slice(test_array, 4.5, 4.5, 1), slice(4, 6))
        self.assertEqual(array_slice(test_array, 2.5, 7.5, 1), slice(2, 9))

    def test_array_slice_sorted(self):
        test_array = arange(11, dtype='float')
        test_array *= test_array
        self.assertEqual(array_slice(test_array, -1, 101, 0), slice(0, 11))
        self.assertEqual(array_slice(test_array, -1, 25, 0), slice(0, 6))
        self.assertEqual(array_slice(test_array, -1, 22, 0), slice(0, 5))
        self.assertEqual(array_slice(test_array, 25, 101, 0), slice(5, 11))
        self.assertEqual(array_slice(test_array, 28, 101, 0), slice(6, 11))
        self.assertEqual(array_slice(test_array, 25, 25, 0), slice(5, 6))
        self.assertEqual(array_slice(test_array, 23, 28, 0), slice(5, 6))
        self.assertEqual(array_slice(test_array, 23, 23, 0), slice(5, 5))
        self.assertEqual(array_slice(test_array, 7, 56, 0), slice(3, 8))

        self.assertEqual(array_slice(test_array, -1, 101, 1), slice(0, 11))
        self.assertEqual(array_slice(test_array, -1, 25, 1), slice(0, 7))
        self.assertEqual(array_slice(test_array, -1, 22, 1), slice(0, 6))
        self.assertEqual(array_slice(test_array, 25, 101, 1), slice(4, 11))
        self.assertEqual(array_slice(test_array, 28, 101, 1), slice(5, 11))
        self.assertEqual(array_slice(test_array, 25, 25, 1), slice(4, 7))
        self.assertEqual(array_slice(test_array, 23, 28, 1), slice(4, 7))
        self.assertEqual(array_slice(test_array, 23, 23, 1), slice(4, 6))
        self.assertEqual(array_slice(test_array, 7, 56, 1), slice(2, 9))

if __name__ == "__main__":
    main()
