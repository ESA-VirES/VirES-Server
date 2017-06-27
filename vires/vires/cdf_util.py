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
from datetime import timedelta
from numpy import (
    amin, amax, nan, vectorize, object as dt_object, float64 as dt_float64,
    ndarray, searchsorted,
)
import scipy
from scipy.interpolate import interp1d
import spacepy
from spacepy import pycdf
from . import FULL_PACKAGE_NAME
from .util import full
from .time_util import (
    mjd2000_to_decimal_year, year_to_day2k, days_per_year,
    datetime, naive_to_utc,
)

CDF_EPOCH_TYPE = pycdf.const.CDF_EPOCH.value
CDF_DOUBLE_TYPE = pycdf.const.CDF_DOUBLE.value
CDF_UINT1_TYPE = pycdf.const.CDF_UINT1.value
CDF_UINT2_TYPE = pycdf.const.CDF_UINT2.value
CDF_UINT4_TYPE = pycdf.const.CDF_UINT4.value
CDF_INT1_TYPE = pycdf.const.CDF_INT1.value
CDF_INT2_TYPE = pycdf.const.CDF_INT2.value
CDF_INT4_TYPE = pycdf.const.CDF_INT4.value

CDF_EPOCH_1970 = 62167219200000.0
CDF_EPOCH_2000 = 63113904000000.0

CDF_CREATOR = "%s [%s-%s, libcdf-%s]" % (
    FULL_PACKAGE_NAME, spacepy.__name__, spacepy.__version__,
    "%s.%s.%s-%s" % pycdf.lib.version
)


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
                return lambda v: v.isoformat("T") + "Z"
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
            # add extra attributes
            cdf.attrs.update({
                "CREATOR": CDF_CREATOR,
                "CREATED": naive_to_utc(
                    datetime.utcnow().replace(microsecond=0)
                ).isoformat().replace("+00:00", "Z"),
            })
    else:
        raise ValueError("Invalid mode value %r!" % mode)
    return cdf


def cdf_rawtime_to_timedelta(raw_time_delta, cdf_type):
    """ Covert a CDF raw time difference to `datetime.timedelta` object """
    if cdf_type == CDF_EPOCH_TYPE:
        # TODO: handle vectors
        return timedelta(seconds=raw_time_delta*1e-3)
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def timedelta_to_cdf_rawtime(time_delta, cdf_type):
    """ Covert `datetime.timedelta` object to CDF raw time scale. """
    if cdf_type == CDF_EPOCH_TYPE:
        # TODO: handle vectors
        return time_delta.total_seconds() * 1e3
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def datetime_to_cdf_rawtime(time, cdf_type):
    """ Convert `datetime.datetime` object to CDF raw time. """
    if cdf_type == CDF_EPOCH_TYPE:
        if isinstance(time, ndarray):
            return pycdf.lib.v_datetime_to_epoch(time)
        else:
            return pycdf.lib.datetime_to_epoch(time)
    else:
        raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_datetime(raw_time, cdf_type):
    """ Convert array of CDF raw time values to array of `dateitme`. """
    if cdf_type == CDF_EPOCH_TYPE:
        if isinstance(raw_time, ndarray):
            return pycdf.lib.v_epoch_to_datetime(raw_time)
        else:
            return pycdf.lib.epoch_to_datetime(raw_time)
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


def mjd2000_to_cdf_rawtime(time, cdf_type):
    """ Convert array of CDF raw time values to array of MJD2000 values. """
    if cdf_type == CDF_EPOCH_TYPE:
        return CDF_EPOCH_2000 + time * 86400000.0
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


def cdf_time_subset(cdf, start, stop, fields, margin=0, time_field='time'):
    """ Extract subset of the listed `fields` from a CDF data file.
    The extracted range of values match times which lie within the given
    closed time interval. The time interval is defined by the MDJ2000 `start`
    and `stop` values.
    The `margin` parameter is used to extend the index range by N surrounding
    elements. Negative margin is allowed.
    """
    idx_start, idx_stop = array_slice(
        cdf.raw_var(time_field)[:], start, stop, margin
    )
    return [(field, cdf[field][idx_start:idx_stop]) for field in fields]


def cdf_time_interp(cdf, time, fields, min_len=2, time_field='time',
                    nodata=None, types=None, **interp1d_prm):
    """ Read values of the listed fields from the CDF file and interpolate
    them at the given time values (the `time` array of MDJ2000 values).
    The data exceeding the time interval of the source data is filled with the
    `nodata` dictionary. The function accepts additional keyword arguments which
    are passed to the `scipy.interpolate.interp1d` interpolation (e.g., `kind`).
    """
    nodata = nodata or {}
    types = types or {}

    # additional interpolation parameters
    if scipy.__version__ >= '0.14':
        interp1d_prm['assume_sorted'] = True
    interp1d_prm['copy'] = False
    interp1d_prm['bounds_error'] = False

    cdf_time = cdf.raw_var(time_field)[:]

    # if possible get subset of the time data
    if time.size > 0 and cdf_time.shape[0] > min_len:
        idx_start, idx_stop = array_slice(
            cdf_time, amin(time), amax(time), min_len//2
        )
        cdf_time = cdf_time[idx_start:idx_stop]

    # check minimal length required by the chosen kind of interpolation
    if time.size > 0 and cdf_time.shape[0] >= min_len:
        return [
            (field, data.astype(type_) if type_ else data)
            for field, data, type_ in (
                (
                    field,
                    interp1d(
                        cdf_time, cdf[field][idx_start:idx_stop],
                        fill_value=nodata.get(field, nan), **interp1d_prm
                    )(time),
                    types.get(field)
                ) for field in fields
            )
        ]
    else:
        return [
            (field, full(
                time.shape, nodata.get(field, nan), types.get(field, 'float')
            )) for field in fields
        ]


def array_slice(values, start, stop, margin=0):
    """ Get sub-setting slice bounds. The sliced array must be sorted
    in the ascending order.
    """
    size = values.shape[0]
    idx_start, idx_stop = 0, size

    if start > stop:
        start, stop = stop, start

    if idx_stop > 0:
        idx_start = searchsorted(values, start, 'left')
        idx_stop = searchsorted(values, stop, 'right')

    if margin != 0:
        if idx_start < size:
            idx_start = min(size, max(0, idx_start - margin))
        if idx_stop > 0:
            idx_stop = min(size, max(0, idx_stop + margin))

    return idx_start, idx_stop
