#-------------------------------------------------------------------------------
#
# Testing Auxiliary Kp Index File Handling
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
# pylint: disable=missing-docstring,invalid-name

from unittest import TestCase, main
from os import remove
from os.path import exists
from io import StringIO
from numpy import array, linspace
from numpy.testing import assert_equal
from scipy.interpolate import interp1d
from vires.aux_kp import update_kp, KpReader
from vires.time_util import mjd2000_to_datetime


TEST_KP = """
# Expanded and assembled Kp and ap
#   Test sample.
#   Flags: Definitive, Quicklook
#   MJD2000 Kp  ap Flag
  -729.9375  7   3    D
  -729.8125 13   5    D
  -729.6875 27  12    D
  -729.5625  7   3    D
  -729.4375  7   3    D
  -729.3125  7   3    D
  -729.1875  3   2    D
  -729.0625  7   3    D
  -728.9375 10   4    D
  -728.8125 20   7    D
  -728.6875 13   5    D
  -728.5625  7   3    D
"""

DATA_KP = {
    'time': array([
        -729.9375, -729.8125, -729.6875, -729.5625, -729.4375, -729.3125,
        -729.1875, -729.0625, -728.9375, -728.8125, -728.6875, -728.5625,
    ]),
    'kp': array([
        7, 13, 27, 7, 7, 7, 3, 7, 10, 20, 13, 7
    ]),
}


class TestIndexKp(TestCase):
    FILE = "./test_tmp_Kp.cdf"

    def setUp(self):
        update_kp(StringIO(TEST_KP), self.FILE)

    def tearDown(self):
        if exists(self.FILE):
            remove(self.FILE)

    def _test_query_kp(self, start, stop, idx_start, idx_stop):
        data = KpReader(self.FILE).subset(
            mjd2000_to_datetime(start), mjd2000_to_datetime(stop)
        )
        assert_equal(data['time'], DATA_KP['time'][idx_start:idx_stop])
        assert_equal(data['kp'], DATA_KP['kp'][idx_start:idx_stop])

    def _test_query_kp_int(self, start, stop, count):
        times = linspace(start, stop, count)
        data = KpReader(self.FILE).interpolate(times)
        expected_values = interp1d(
            DATA_KP['time'], DATA_KP['kp'], bounds_error=False, kind="previous"
        )(times)
        assert_equal(data['kp'], expected_values)

    def test_query_kp_int_full_overlap(self):
        self._test_query_kp_int(-730.00, -728.00, 20)

    def test_query_kp_int_touched_lower(self):
        self._test_query_kp_int(-728.5626, -728.00, 5)

    def test_query_kp_int_touched_uppper(self):
        self._test_query_kp_int(-730.00, -729.9374, 5)

    def test_query_kp_int_no_overlap_lower(self):
        self._test_query_kp_int(-728.00, -726.00, 5)

    def test_query_kp_int_no_overlap_uppper(self):
        self._test_query_kp_int(-734.00, -732.00, 5)

    def test_query_kp_int_single_value(self):
        self._test_query_kp_int(-729.00, -729.00, 1)

    def test_query_kp_full_exact(self):
        self._test_query_kp(-729.9375, -728.5625, 0, 12)

    def test_query_kp_full_far(self):
        self._test_query_kp(-731.00, -728.00, 0, 12)

    def test_query_kp_full_close(self):
        self._test_query_kp(-729.93, -728.57, 0, 12)

    def test_query_kp_subset_innner(self):
        self._test_query_kp(-729.60, -729.00, 2, 9)

    def test_query_kp_subset_lower(self):
        self._test_query_kp(-733.00, -729.00, 0, 9)

    def test_query_kp_subset_upper(self):
        self._test_query_kp(-729.60, -725.00, 2, 12)

    def test_query_kp_no_overlap_lower_close(self):
        self._test_query_kp(-733.00, -729.94, 0, 0)

    def test_query_kp_no_overlap_lower_far(self):
        self._test_query_kp(-733.00, -732.00, 0, 0)

    def test_query_kp_no_overlap_upper_close(self):
        self._test_query_kp(-728.55, -725.00, 0, 0)

    def test_query_kp_no_overlap_upper_far(self):
        self._test_query_kp(-724.00, -725.00, 0, 0)


if __name__ == "__main__":
    main()
