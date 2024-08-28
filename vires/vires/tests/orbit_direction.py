#-------------------------------------------------------------------------------
#
# Orbit direction file handling - test
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
from datetime import datetime
from numpy import round as around, linspace
from numpy.testing import assert_equal
from scipy.interpolate import interp1d
from vires.cdf_util import cdf_open, datetime_to_cdf_rawtime, CDF_EPOCH_TYPE
from vires.tests.data import TEST_ORBIT_DIRECTION_CDF
from vires.orbit_direction import OrbitDirectionReader

FIELD_TIME = OrbitDirectionReader.TIME_FIELD
FIELDS_ALL = (FIELD_TIME,) + OrbitDirectionReader.DATA_FIELDS

INT_CONF_ORBIT_DIRECTION = {
    "OrbitDirection": {
        'kind': 'previous',
        'dtype': 'int8',
        'nodata': 0,
    },
    "BoundaryType": {
        'kind': 'previous',
        'dtype': 'int8',
        'nodata': -1,
    },
}


class TestOrbitDirection(TestCase):
    FILES = [TEST_ORBIT_DIRECTION_CDF]

    def _get_reference_data(self):
        with cdf_open(self.FILES[0]) as cdf:
            data = {
                field: cdf.raw_var(field)[...]
                for field in FIELDS_ALL
            }
        return data

    def _test_fetch(self, start, stop, slice_):
        reference_dataset = self._get_reference_data()
        tested_dataset = OrbitDirectionReader(*self.FILES).subset(start, stop)
        for field, reference in reference_dataset.items():
            data = tested_dataset[field]
            assert_equal(data, reference[slice_])

    def _test_interpolate(self, start, stop, count):
        times = around(linspace(
            datetime_to_cdf_rawtime(start, CDF_EPOCH_TYPE),
            datetime_to_cdf_rawtime(stop, CDF_EPOCH_TYPE),
            count,
        ))
        reference_dataset = self._get_reference_data()
        tested_dataset = OrbitDirectionReader(*self.FILES).interpolate(times)

        for field, conf in INT_CONF_ORBIT_DIRECTION.items():
            data = tested_dataset[field]
            reference = interp1d(
                reference_dataset[FIELD_TIME], reference_dataset[field],
                bounds_error=False, kind=conf['kind'],
                fill_value=conf['nodata'],
            )(times).astype(conf['dtype'])
            assert_equal(data, reference)

    def test_fetch_all_with_margin(self):
        self._test_fetch(
            datetime(2016, 12, 30), datetime(2017, 1, 2), Ellipsis
        )

    def test_fetch_exact(self):
        self._test_fetch(
            datetime(2016, 12, 31), datetime(2017, 1, 1), Ellipsis
        )

    def test_fetch_partial_inner_long(self):
        self._test_fetch(
            datetime(2016, 12, 31, 8), datetime(2016, 12, 31, 20),
            slice(11, 28)
        )

    def test_fetch_partial_inner_short(self):
        self._test_fetch(
            datetime(2016, 12, 31, 12),
            datetime(2016, 12, 31, 12),
            slice(16, 18)
        )

    def test_fetch_partial_lower(self):
        self._test_fetch(
            datetime(2016, 12, 30), datetime(2016, 12, 31, 8), slice(None, 13)
        )

    def test_fetch_partial_upper(self):
        self._test_fetch(
            datetime(2016, 12, 31, 20), datetime(2017, 1, 2), slice(26, None)
        )

    def test_fetch_touch_lower(self):
        self._test_fetch(
            datetime(2016, 12, 30), datetime(2016, 12, 31), slice(None, 2)
        )

    def test_fetch_touch_upper(self):
        self._test_fetch(
            datetime(2017, 1, 1), datetime(2017, 1, 2), slice(-2, None)
        )

    def test_fetch_none_lower(self):
        self._test_fetch(
            datetime(2016, 12, 30), datetime(2016, 12, 30, 12), []
        )

    def test_fetch_none_upper(self):
        self._test_fetch(
            datetime(2017, 1, 1, 12), datetime(2017, 1, 2), []
        )


    def test_interpolate_all_with_margin(self):
        self._test_interpolate(
            datetime(2016, 12, 30), datetime(2017, 1, 2), 25
        )

    def test_interpolate_exact(self):
        self._test_interpolate(
            datetime(2016, 12, 31), datetime(2017, 1, 1), 25
        )

    def test_interpolate_partial_inner_long(self):
        self._test_interpolate(
            datetime(2016, 12, 31, 8), datetime(2016, 12, 31, 20), 10
        )

    def test_interpolate_partial_inner_short(self):
        self._test_interpolate(
            datetime(2016, 12, 31, 12), datetime(2016, 12, 31, 12), 10
        )

    def test_interpolate_partial_lower(self):
        self._test_interpolate(
            datetime(2016, 12, 30), datetime(2016, 12, 31, 8), 10
        )

    def test_interpolate_partial_upper(self):
        self._test_interpolate(
            datetime(2016, 12, 31, 20), datetime(2017, 1, 2), 10
        )

    def test_interpolate_touch_lower(self):
        self._test_interpolate(
            datetime(2016, 12, 30), datetime(2016, 12, 31), 10
        )

    def test_interpolate_touch_upper(self):
        self._test_interpolate(
            datetime(2017, 1, 1), datetime(2017, 1, 2), 5
        )

    def test_interpolate_none_lower(self):
        self._test_interpolate(
            datetime(2016, 12, 30), datetime(2016, 12, 30, 12), 5
        )

    def test_interpolate_none_upper(self):
        self._test_interpolate(
            datetime(2017, 1, 1, 12), datetime(2017, 1, 2), 5
        )


class TestOrbitDirectionMultiFile(TestOrbitDirection):
    FILES = [TEST_ORBIT_DIRECTION_CDF, TEST_ORBIT_DIRECTION_CDF]


if __name__ == "__main__":
    main()
