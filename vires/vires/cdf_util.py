#-------------------------------------------------------------------------------
#
# CDF file-format utilities
#
# Project: VirES-Server
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

from os.path import exists
from math import ceil, floor
from numpy import (
    amin, amax, nan, vectorize, object as dt_object, float64 as dt_float64,
)
import scipy
from scipy.interpolate import interp1d
from spacepy import pycdf
from .util import full
from .time_util import mjd2000_to_decimal_year, year_to_day2k, days_per_year

CDF_EPOCH_TYPE = pycdf.const.CDF_EPOCH.value
CDF_DOUBLE_TYPE = pycdf.const.CDF_DOUBLE.value

CDF_EPOCH_1970 = 62167219200000.0
CDF_EPOCH_2000 = 63113904000000.0


def get_formatter(data, cdf_type=CDF_DOUBLE_TYPE):
    """ Second order function returning optimal data-type string formatter
    function.
    """
    if cdf_type is None:
        cdf_type = CDF_DOUBLE_TYPE
    def _get_formater(shape, dtype, cdf_type):
        if len(shape) > 1:
            value_formater = _get_formater(shape[1:], dtype, cdf_type)
            def formater(arr):
                " vector formatter "
                return "{%s}" % ";".join(
                    value_formater(value) for value in arr
                )
            return formater
        elif cdf_type == CDF_DOUBLE_TYPE:
            return lambda v: "%.9g" % v
        elif cdf_type == CDF_EPOCH_TYPE:
            if dtype == dt_float64:
                return lambda v: "%.14g" % v
            elif dtype == dt_object:
                return lambda v: v.isoformat(" ")
            else:
                return str
        else:
            return str
    return _get_formater(data.shape, data.dtype, cdf_type)


def cdf_open(filename, mode="r"):
    """ Open a new or an existing  CDF file.
    Allowed modes are 'r' (read-only) and 'w' (read-write).
    A new CDF file is created in for the 'w' mode if it does not exist.
    The returned object can be used with the `with` command.
    """
    if mode == "r":
        cdf = pycdf.CDF(filename)
    elif mode == "w":
        if exists(filename):
            cdf = pycdf.CDF(filename)
            cdf.readonly(False)
        else:
            cdf = pycdf.CDF(filename, "")
    else:
        raise ValueError("Invalid mode value %r!" % mode)
    return cdf


def cdf_rawtime_to_datetime(raw_time, cdf_type):
    """ Convert array of CDF raw time values to array of `dateitme`. """
    if cdf_type == CDF_EPOCH_TYPE:
        return pycdf.lib.v_epoch_to_datetime(raw_time)
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_unix_epoch(raw_time, cdf_type):
    """ Convert array of CDF raw time values to array of MJD2000 values. """
    if cdf_type == CDF_EPOCH_TYPE:
        return (raw_time - CDF_EPOCH_1970) * 1e-3
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_mjd2000(raw_time, cdf_type):
    """ Convert array of CDF raw time values to array of MJD2000 values. """
    if cdf_type == CDF_EPOCH_TYPE:
        return (raw_time - CDF_EPOCH_2000) / 86400000.0
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_decimal_year_fast(raw_time, cdf_type, year):
    """ Convert array of CDF raw time values to array of decimal years.
    This function expect all dates to of the same year and this year has
    to be provided as a parameter.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        year_offset = year_to_day2k(year) * 86400000.0 + CDF_EPOCH_2000
        year_length = days_per_year(year) * 86400000.0
        return year + (raw_time - year_offset) / year_length
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_decimal_year(raw_time, cdf_type):
    """ Convert array of CDF raw time values to array of decimal years.
    """
    v_mjd2000_to_decimal_year = vectorize(
        mjd2000_to_decimal_year, otypes=(dt_float64,)
    )
    return v_mjd2000_to_decimal_year(cdf_rawtime_to_mjd2000(raw_time, cdf_type))


def _cdf_time_slice(cdf, start, stop, margin=0, time_field='time'):
    """ Get sub-setting slice bounds. """
    time = cdf.raw_var(time_field)
    idx_start, idx_stop = 0, time.shape[0]

    if start > stop:
        start, stop = stop, start

    if time.shape[0] > 0:
        start = max(start, time[0])
        stop = min(stop, time[-1])
        time_span = time[-1] - time[0]
        if time_span > 0:
            resolution = (time.shape[0] - 1) / time_span
            idx_start = int(ceil((start - time[0]) * resolution))
            idx_stop = max(0, 1 + int(floor((stop - time[0]) * resolution)))
        elif start > time[-1] or stop < time[0]:
            idx_start = idx_stop # empty selection

    if margin != 0:
        if idx_start < time.shape[0]:
            idx_start = max(0, idx_start - margin)
        if idx_stop > 0:
            idx_stop = max(0, idx_stop + margin)

    return idx_start, idx_stop


def cdf_time_subset(cdf, start, stop, fields, margin=0, time_field='time'):
    """ Extract subset of the listed `fields` from a CDF data file.
    The extracted range of values match times which lie within the given
    closed time interval. The time interval is defined by the MDJ2000 `start`
    and `stop` values.
    The `margin` parameter is used to extend the index range by N surrounding
    elements. Negative margin is allowed.
    """
    idx_start, idx_stop = _cdf_time_slice(
        cdf, start, stop, margin, time_field
    )
    return [(field, cdf[field][idx_start:idx_stop]) for field in fields]


def cdf_time_interp(cdf, time, fields, min_len=2, time_field='time',
                    **interp1d_prm):
    """ Read values of the listed fields from the CDF file and interpolate
    them at the given time values (the `time` array of MDJ2000 values).
    The data exceeding the time interval of the source data is filled with the
    `fill_value`. The function accepts additional keyword arguments which are
    passed to the `scipy.interpolate.interp1d` interpolation (such as `kind`
    and `fill_value`).
    """
    # additional interpolation parameters
    if scipy.__version__ >= '0.14':
        interp1d_prm['assume_sorted'] = True
    interp1d_prm['copy'] = False
    interp1d_prm['bounds_error'] = False

    cdf_time = cdf.raw_var(time_field)

    # if possible get subset of the time data
    if time.size > 0 and cdf_time.shape[0] > min_len:
        idx_start, idx_stop = _cdf_time_slice(
            cdf, amin(time), amax(time), min_len//2, time_field
        )
        cdf_time = cdf_time[idx_start:idx_stop]

    # check minimal length required by the chosen kind of interpolation
    if time.size > 0 and cdf_time.shape[0] >= min_len:
        return [
            (field, interp1d(
                cdf_time, cdf[field][idx_start:idx_stop], **interp1d_prm
            )(time))
            for field in fields
        ]
    else:
        return [
            (field, full(time.shape, interp1d_prm.get("fill_value", nan)))
            for field in fields
        ]
