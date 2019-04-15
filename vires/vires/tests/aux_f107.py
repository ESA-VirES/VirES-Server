#-------------------------------------------------------------------------------
#
# Testing # AUX_F107_2_ index file handling.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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
from StringIO import StringIO
from numpy import array, linspace
from numpy.testing import assert_equal
from scipy.interpolate import interp1d
from vires.aux_f107 import (
    update_aux_f107_2_, F10_2_Reader,
)
from vires.time_util import mjd2000_to_datetime

FIELD_TIME = "MJD2000"
FIELD_F107 = "F10.7"

TEST_AUX_F10_2_ = """
# Assembled daily observed values of solar flux F10.7
# obtained from ftp://ftp.ngdc.noaa.gov/STP/space-weather/solar-data/solar-features/solar-radio/noontime-flux/penticton/penticton_observed/listings/listing_drao_noontime-flux-observed_daily.txt
# on 15-May-2018 05:00:25 by program process_F107
# MD2000 F10.7  in units of [10e-22 W m^-2 Hz^-1 ]
  6660.5   68.3
  6661.5   68.6
  6662.5   69.0
  6663.5   68.8
  6664.5   69.0
  6665.5   69.0
  6666.5   68.4
  6667.5   67.8
  6668.5   68.5
  6669.5   66.4
  6670.5   67.3
  6671.5   66.8
  6672.5   67.9
  6673.5   68.7
  6674.5   68.5
  6675.5   68.3
  6676.5   70.0
  6677.5   69.7
  6678.5   69.5
  6679.5   70.6
  6680.5   69.2
  6681.5   69.3
  6682.5   70.8
  6683.5   70.8
  6684.5   73.0
  6685.5   76.8
  6686.5   75.7
  6687.5   73.9
  6688.5   72.9
  6689.5   70.8
  6690.5   69.4
  6691.5   68.7
  6692.5   70.2
  6693.5   71.1
  6694.5   70.2
"""

DATA_AUX_F10_2_ = {
    FIELD_TIME: array([
        6660.5, 6661.5, 6662.5, 6663.5, 6664.5, 6665.5, 6666.5, 6667.5, 6668.5,
        6669.5, 6670.5, 6671.5, 6672.5, 6673.5, 6674.5, 6675.5, 6676.5, 6677.5,
        6678.5, 6679.5, 6680.5, 6681.5, 6682.5, 6683.5, 6684.5, 6685.5, 6686.5,
        6687.5, 6688.5, 6689.5, 6690.5, 6691.5, 6692.5, 6693.5, 6694.5,
    ]),
    FIELD_F107: array([
        68.3, 68.6, 69.0, 68.8, 69.0, 69.0, 68.4, 67.8, 68.5, 66.4, 67.3, 66.8,
        67.9, 68.7, 68.5, 68.3, 70.0, 69.7, 69.5, 70.6, 69.2, 69.3, 70.8, 70.8,
        73.0, 76.8, 75.7, 73.9, 72.9, 70.8, 69.4, 68.7, 70.2, 71.1, 70.2,
    ]),
}

class TestIndexDst(TestCase):
    FILE = "./test_tmp_aux_f10_2_.cdf"

    def setUp(self):
        update_aux_f107_2_(StringIO(TEST_AUX_F10_2_), self.FILE)

    def tearDown(self):
        if exists(self.FILE):
            remove(self.FILE)

    def test(self):
        pass

    def _test_query_f107(self, start, stop, idx_start, idx_stop):
        data = F10_2_Reader(self.FILE).subset(
            mjd2000_to_datetime(start), mjd2000_to_datetime(stop)
        )
        assert_equal(
            data[FIELD_TIME], DATA_AUX_F10_2_[FIELD_TIME][idx_start:idx_stop]
        )
        assert_equal(
            data[FIELD_F107], DATA_AUX_F10_2_[FIELD_F107][idx_start:idx_stop]
        )

    def _test_query_f107_int(self, start, stop, count):
        times = linspace(start, stop, count)
        data = F10_2_Reader(self.FILE).interpolate(times)
        expected_values = interp1d(
            DATA_AUX_F10_2_[FIELD_TIME], DATA_AUX_F10_2_[FIELD_F107],
            bounds_error=False
        )(times)
        assert_equal(data[FIELD_F107], expected_values)

    def test_query_aux_f107_2__int_full_overlap(self):
        self._test_query_f107_int(6660, 6695, 71)

    def test_query_aux_f107_2__int_touched_lower(self):
        self._test_query_f107_int(6660.0, 6660.5, 5)

    def test_query_aux_f107_2__int_touched_uppper(self):
        self._test_query_f107_int(6694.5, 6695.0, 5)

    def test_query_aux_f107_2__int_no_overlap_lower(self):
        self._test_query_f107_int(6659.0, 6660.0, 5)

    def test_query_aux_f107_2__int_no_overlap_uppper(self):
        self._test_query_f107_int(6695.0, 6696.0, 5)

    def test_query_aux_f107_2__int_single_value(self):
        self._test_query_f107_int(6680.0, 6680.0, 1)

    def test_query_aux_f107_2__full_exact(self):
        self._test_query_f107(6660.5, 6694.5, 0, 35)

    def test_query_aux_f107_2__full_far(self):
        self._test_query_f107(6600.0, 67000.0, 0, 35)

    def test_query_aux_f107_2__full_close(self):
        self._test_query_f107(6660.49, 6694.51, 0, 35)

    def test_query_aux_f107_2__subset_innner(self):
        self._test_query_f107(6670.0, 6680.0, 9, 21)

    def test_query_aux_f107_2__subset_lower(self):
        self._test_query_f107(6600.0, 6680.0, 0, 21)

    def test_query_aux_f107_2__subset_upper(self):
        self._test_query_f107(6680.0, 6700.0, 19, 35)

    def test_query_aux_f107_2__no_overlap_lower_close(self):
        self._test_query_f107(6600.0, 6660.49, 0, 0)

    def test_query_aux_f107_2__no_overlap_lower_far(self):
        self._test_query_f107(6600.0, 6650.0, 0, 0)

    def test_query_aux_f107_2__no_overlap_upper_close(self):
        self._test_query_f107(6694.51, 67000.0, 0, 0)

    def test_query_aux_f107_2__no_overlap_upper_far(self):
        self._test_query_f107(6699.0, 67000.0, 0, 0)


if __name__ == "__main__":
    main()
