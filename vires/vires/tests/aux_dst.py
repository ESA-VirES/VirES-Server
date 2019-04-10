#-------------------------------------------------------------------------------
#
# Testing Auxiliary Dst Index File Handling
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

from unittest import TestCase, main
from os import remove
from os.path import exists
from StringIO import StringIO
from numpy import array, linspace
from numpy.testing import assert_equal
from scipy.interpolate import interp1d
from vires.aux_dst import update_dst, DstReader
from vires.time_util import mjd2000_to_datetime


TEST_DST = """
# Expanded and assembled Dst, Est and Ist, Zero Mean
# Test sample.
#  MJD2000       Dst       Est       Ist   Flag
  -729.97917    -9.000   -11.130     2.130    D
  -729.93750    -8.000   -10.323     2.323    D
  -729.89583    -9.000   -10.978     1.978    D
  -729.85417    -9.000   -10.938     1.938    D
  -729.81250   -13.000   -13.779     0.779    D
  -729.77083   -16.000   -15.934    -0.066    D
  -729.72917   -20.000   -18.820    -1.180    D
  -729.68750   -26.000   -23.160    -2.840    D
  -729.64583   -30.000   -26.090    -3.910    D
  -729.60417   -30.000   -26.150    -3.850    D
  -729.56250   -30.000   -26.188    -3.812    D
  -729.52083   -21.000   -19.750    -1.250    D
  -729.47917   -15.000   -15.400     0.400    D
  -729.43750   -13.000   -13.906     0.906    D
  -729.39583   -12.000   -13.141     1.141    D
  -729.35417   -14.000   -14.542     0.542    D
  -729.31250   -17.000   -16.685    -0.315    D
  -729.27083   -18.000   -17.411    -0.589    D
  -729.22917   -12.000   -13.107     1.107    D
  -729.18750   -10.000   -11.631     1.631    D
  -729.14583   -11.000   -12.313     1.313    D
  -729.10417   -14.000   -14.451     0.451    D
  -729.06250   -19.000   -18.049    -0.951    D
  -729.02083   -16.000   -15.926    -0.074    D
  -728.97917   -12.000   -13.047     1.047    D
  -728.93750    -9.000   -10.862     1.862    D
  -728.89583   -11.000   -12.262     1.262    D
  -728.85417   -11.000   -12.251     1.251    D
  -728.81250    -9.000   -10.803     1.803    D
  -728.77083    -9.000   -10.780     1.780    D
  -728.72917   -15.000   -15.074     0.074    D
  -728.68750   -19.000   -17.976    -1.024    D
  -728.64583   -21.000   -19.453    -1.547    D
  -728.60417   -20.000   -18.770    -1.230    D
  -728.56250   -18.000   -17.350    -0.650    D
"""

DATA_DST = {
    'time': array([
        -729.97917, -729.93750, -729.89583, -729.85417, -729.81250, -729.77083,
        -729.72917, -729.68750, -729.64583, -729.60417, -729.56250, -729.52083,
        -729.47917, -729.43750, -729.39583, -729.35417, -729.31250, -729.27083,
        -729.22917, -729.18750, -729.14583, -729.10417, -729.06250, -729.02083,
        -728.97917, -728.93750, -728.89583, -728.85417, -728.81250, -728.77083,
        -728.72917, -728.68750, -728.64583, -728.60417, -728.56250,
    ]),
    'dst': array([
        -9.000, -8.000, -9.000, -9.000, -13.000, -16.000, -20.000, -26.000,
        -30.000, -30.000, -30.000, -21.000, -15.000, -13.000, -12.000, -14.000,
        -17.000, -18.000, -12.000, -10.000, -11.000, -14.000, -19.000, -16.000,
        -12.000, -9.000, -11.000, -11.000, -9.000, -9.000, -15.000, -19.000,
        -21.000, -20.000, -18.000,
    ]),
}

class TestIndexDst(TestCase):
    FILE = "./test_tmp_Dst.cdf"

    def setUp(self):
        update_dst(StringIO(TEST_DST), self.FILE)

    def tearDown(self):
        if exists(self.FILE):
            remove(self.FILE)

    def _test_query_dst(self, start, stop, idx_start, idx_stop):
        data = DstReader(self.FILE).subset(
            mjd2000_to_datetime(start), mjd2000_to_datetime(stop)
        )
        assert_equal(data['time'], DATA_DST['time'][idx_start:idx_stop])
        assert_equal(data['dst'], DATA_DST['dst'][idx_start:idx_stop])

    def _test_query_dst_int(self, start, stop, count):
        times = linspace(start, stop, count)
        data = DstReader(self.FILE).interpolate(times)
        expected_values = interp1d(
            DATA_DST['time'], DATA_DST['dst'], bounds_error=False
        )(times)
        assert_equal(data['dst'], expected_values)

    def test_query_dst_int_full_overlap(self):
        self._test_query_dst_int(-732.00, -728.00, 80)

    def test_query_dst_int_touched_lower(self):
        self._test_query_dst_int(-732.00, -729.979169, 5)

    def test_query_dst_int_touched_uppper(self):
        self._test_query_dst_int(-728.56251, -728.00, 5)

    def test_query_dst_int_no_overlap_lower(self):
        self._test_query_dst_int(-734.00, -732.00, 5)

    def test_query_dst_int_no_overlap_uppper(self):
        self._test_query_dst_int(-728.00, -726.00, 5)

    def test_query_dst_int_single_value(self):
        self._test_query_dst_int(-729.00, -729.00, 1)

    def test_query_dst_full_exact(self):
        self._test_query_dst(-729.97917, -728.56250, 0, 35)

    def test_query_dst_full_far(self):
        self._test_query_dst(-731.00, -728.00, 0, 35)

    def test_query_dst_full_close(self):
        self._test_query_dst(-729.97, -728.57, 0, 35)

    def test_query_dst_subset_innner(self):
        self._test_query_dst(-729.60, -729.00, 9, 25)

    def test_query_dst_subset_lower(self):
        self._test_query_dst(-733.00, -729.00, 0, 25)

    def test_query_dst_subset_upper(self):
        self._test_query_dst(-729.60, -725.00, 9, 35)

    def test_query_dst_no_overlap_lower_close(self):
        self._test_query_dst(-733.00, -730.00, 0, 0)

    def test_query_dst_no_overlap_lower_far(self):
        self._test_query_dst(-733.00, -732.00, 0, 0)

    def test_query_dst_no_overlap_upper_close(self):
        self._test_query_dst(-728.54, -725.00, 0, 0)

    def test_query_dst_no_overlap_upper_far(self):
        self._test_query_dst(-724.00, -725.00, 0, 0)


if __name__ == "__main__":
    main()
