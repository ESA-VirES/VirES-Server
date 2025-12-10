#-------------------------------------------------------------------------------
#
# JSON input time parsers
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
# pylint: disable=

from numpy import vectorize, asarray, datetime64, timedelta64
from django.utils.dateparse import parse_datetime
from eoxmagmod import decimal_year_to_mjd2000
from vires.time_util import (
    utc_to_naive,
    datetime_to_mjd2000,
    unix_epoch_to_mjd2000,
)
from vires.time_cdf_epoch import cdf_epoch_to_mjd2000
from vires.time_cdf_tt2000 import cdf_tt2000_to_mjd2000


def iso_datetime_to_mjd2000(value):
    """ Convert ISO 8601 datetime string to MJD2000 time. """
    parsed_value = parse_datetime(value)
    if parsed_value is None:
        raise ValueError("Not a valid ISO-8601 string!")
    return datetime_to_mjd2000(utc_to_naive(parsed_value))


def array_iso_datetime_to_mjd2000(values):
    """ Convert ISO 8601 datetime string to MJD2000 time array. """
    return vectorize(iso_datetime_to_mjd2000, otypes=["float64"])(asarray(values))


def array_unix_epoch_to_mjd2000(values):
    """ Convert number of seconds since 1970-01-01 to MJD2000 time array. """
    return unix_epoch_to_mjd2000(asarray(values, dtype="float64"))


def array_decimal_year_to_mjd2000(values):
    """ Convert decimal years to MJD2000 time array. """
    return decimal_year_to_mjd2000(asarray(values, dtype="float64"))


def array_cdf_epoch_to_mjd2000(values):
    """ Convert CDF_EPOCH values to MJD2000 time array. """
    return cdf_epoch_to_mjd2000(asarray(values, dtype="float64"))


def array_cdf_tt2000_to_mjd2000(values):
    """ Convert CDF_EPOCH values to MJD2000 time array. """
    return cdf_tt2000_to_mjd2000(asarray(values, dtype="int64"))


def array_datetime64_to_mjd2000(precision):
    """ Get conversion function from datetime64 values to MJD2000 time array. """
    dtype = f"datetime64[{precision}]"
    zero_day = datetime64('2000-01-01', precision)
    days_per_unit = 1.0 / (
        timedelta64(1, "D").astype(f"timedelta64[{precision}]").astype("int64")
    )

    def _array_datetime64_to_mjd2000(values):
        return days_per_unit * (
            asarray(values, dtype=dtype) - zero_day
        ).astype("int64")

    return _array_datetime64_to_mjd2000
