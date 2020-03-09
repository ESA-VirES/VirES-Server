#-------------------------------------------------------------------------------
#
# CDF file-format utilities
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
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
# pylint: disable=too-many-arguments

from os.path import exists
from datetime import datetime, timedelta
import ctypes
from numpy import (
    nan, vectorize, object as dt_object, float64 as dt_float64,
    ndarray, searchsorted, asarray, full,
)
import scipy
from scipy.interpolate import interp1d
import spacepy
from spacepy import pycdf
from spacepy.pycdf import CDFError, lib
from . import FULL_PACKAGE_NAME
from .time_util import (
    mjd2000_to_decimal_year, year_to_day2k, days_per_year,
    datetime, naive_to_utc, utc_to_naive,
)

GZIP_COMPRESSION = pycdf.const.GZIP_COMPRESSION
GZIP_COMPRESSION_LEVEL1 = ctypes.c_long(1)

CDF_EPOCH_TYPE = pycdf.const.CDF_EPOCH.value
CDF_EPOCH16_TYPE = pycdf.const.CDF_EPOCH16.value
CDF_TIME_TT2000_TYPE = pycdf.const.CDF_TIME_TT2000.value
CDF_FLOAT_TYPE = pycdf.const.CDF_FLOAT.value
CDF_DOUBLE_TYPE = pycdf.const.CDF_DOUBLE.value
CDF_REAL8_TYPE = pycdf.const.CDF_REAL8.value # CDF_DOUBLE != CDF_REAL8
CDF_REAL4_TYPE = pycdf.const.CDF_REAL4.value # CDF_FLOAT != CDF_REAL4
CDF_UINT1_TYPE = pycdf.const.CDF_UINT1.value
CDF_UINT2_TYPE = pycdf.const.CDF_UINT2.value
CDF_UINT4_TYPE = pycdf.const.CDF_UINT4.value
CDF_INT1_TYPE = pycdf.const.CDF_INT1.value
CDF_INT2_TYPE = pycdf.const.CDF_INT2.value
CDF_INT4_TYPE = pycdf.const.CDF_INT4.value
CDF_INT8_TYPE = pycdf.const.CDF_INT8.value
CDF_CHAR_TYPE = pycdf.const.CDF_CHAR.value

CDF_TYPE_TO_LABEL = {
    CDF_EPOCH_TYPE: "CDF_EPOCH",
    CDF_EPOCH16_TYPE: "CDF_EPOCH16",
    CDF_TIME_TT2000_TYPE: "CDF_TIME_TT2000",
    CDF_FLOAT_TYPE: "CDF_FLOAT",
    CDF_DOUBLE_TYPE: "CDF_DOUBLE",
    CDF_REAL8_TYPE: "CDF_REAL8",
    CDF_REAL4_TYPE: "CDF_REAL4",
    CDF_UINT1_TYPE: "CDF_UINT1",
    CDF_UINT2_TYPE: "CDF_UINT2",
    CDF_UINT4_TYPE: "CDF_UINT4",
    CDF_INT1_TYPE: "CDF_INT1",
    CDF_INT2_TYPE: "CDF_INT2",
    CDF_INT4_TYPE: "CDF_INT4",
    CDF_INT8_TYPE: "CDF_INT8",
    CDF_CHAR_TYPE: "CDF_CHAR",
}

LABEL_TO_CDF_TYPE = {
    label: cdf_type for cdf_type, label in CDF_TYPE_TO_LABEL.items()
}

CDF_TYPE_TO_DTYPE = {
    CDF_EPOCH_TYPE: "datetime64[ms]",
    CDF_FLOAT_TYPE: "float32",
    CDF_DOUBLE_TYPE: "float64",
    CDF_REAL8_TYPE: "float32",
    CDF_REAL4_TYPE: "float64",
    CDF_UINT1_TYPE: "uint8",
    CDF_UINT2_TYPE: "uint16",
    CDF_UINT4_TYPE: "uint32",
    CDF_INT1_TYPE: "int8",
    CDF_INT2_TYPE: "int16",
    CDF_INT4_TYPE: "int32",
    CDF_INT8_TYPE: "int46",
    CDF_CHAR_TYPE: "S",
}

DATETIME_1970 = datetime(1970, 1, 1)
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
        if cdf_type == CDF_DOUBLE_TYPE:
            return lambda v: "%.9g" % v
        if cdf_type == CDF_EPOCH_TYPE:
            if dtype == dt_float64:
                return lambda v: "%.14g" % v
            if dtype == dt_object:
                return lambda v: v.isoformat("T") + "Z"
            return str
        if cdf_type == CDF_CHAR_TYPE:
            return lambda v: v.decode('utf-8')
        return str
    return _get_formater(data.shape, data.dtype, cdf_type)


def is_cdf_file(filename):
    """ Test if file is supported CDF file. """
    try:
        with cdf_open(filename):
            return True
    except CDFError:
        return False


def cdf_open(filename, mode="r"):
    """ Open a new or existing  CDF file.
    Allowed modes are 'r' (read-only) and 'w' (read-write).
    A new CDF file is created if the 'w' mode is chosen and the file does not
    exist.
    The returned object is a context manager which can be used with the `with`
    command.

    NOTE: for the newly created CDF files the pycdf.CDF adds the '.cdf'
    extension to the filename if it does not end by this extension already.
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


def cdf_rawtime_to_seconds(raw_time_delta, cdf_type):
    """ Convert CDF raw time to second. The epoch offset is unchanged.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        # TODO: handle vectors
        return raw_time_delta * 1e-3
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def seconds_to_cdf_rawtime(time_seconds, cdf_type):
    """ Convert time in seconds to CDF raw time. The epoch offset is unchanged.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        # TODO: handle vectors
        return time_seconds * 1e3
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_timedelta(raw_time_delta, cdf_type):
    """ Convert a CDF raw time difference to `datetime.timedelta` object.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        # TODO: handle vectors
        return timedelta(seconds=raw_time_delta*1e-3)
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def timedelta_to_cdf_rawtime(time_delta, cdf_type):
    """ Convert `datetime.timedelta` object to CDF raw time scale.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        # TODO: handle vectors
        return time_delta.total_seconds() * 1e3
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def datetime_to_cdf_rawtime(time, cdf_type):
    """ Convert `datetime.datetime` object to CDF raw time. """
    if cdf_type == CDF_EPOCH_TYPE:
        if isinstance(time, ndarray):
            return vectorize(datetime_to_cdf_epoch, otypes=('float64',))(time)
        return datetime_to_cdf_epoch(time)
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def datetime_to_cdf_epoch(dtobj):
    """ Convert raw CDF_EPOCH values to datetime.datetime object. """
    return (utc_to_naive(dtobj) - DATETIME_1970).total_seconds()*1e3  + CDF_EPOCH_1970


def cdf_rawtime_to_datetime(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to an array
    of `dateitme.datetime` objects.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        if isinstance(raw_time, ndarray):
            return vectorize(cdf_epoch_to_datetime, otypes=('object',))(raw_time)
        return cdf_epoch_to_datetime(raw_time)
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_epoch_to_datetime(cdf_epoch):
    """ Convert raw CDF_EPOCH values to datetime.datetime object. """
    return DATETIME_1970 + timedelta(milliseconds=(cdf_epoch - CDF_EPOCH_1970))


def cdf_rawtime_to_unix_epoch(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to an array of Unix epoch values.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return (raw_time - CDF_EPOCH_1970) * 1e-3
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_mjd2000(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to array of MJD2000 values.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return (raw_time - CDF_EPOCH_2000) / 86400000.0
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def mjd2000_to_cdf_rawtime(time, cdf_type):
    """ Convert an array of MJD2000 values to an array of CDF raw time values.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return CDF_EPOCH_2000 + time * 86400000.0
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_decimal_year_fast(raw_time, cdf_type, year):
    """ Convert an array of CDF raw time values to an array of decimal years.
    This function assumes all dates to be of the same year and this year has
    to be provided as a parameter.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        year_offset = year_to_day2k(year) * 86400000.0 + CDF_EPOCH_2000
        year_length = days_per_year(year) * 86400000.0
        return year + (raw_time - year_offset) / year_length
    raise TypeError("Unsupported CDF time type %r !" % cdf_type)


def cdf_rawtime_to_decimal_year(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to an array of decimal years.
    This function makes not assumption about the year and does the full fledged
    conversion for each item.
    """
    v_mjd2000_to_decimal_year = vectorize(
        mjd2000_to_decimal_year, otypes=(dt_float64,)
    )
    return v_mjd2000_to_decimal_year(cdf_rawtime_to_mjd2000(raw_time, cdf_type))


def cdf_epoch16_to_epoch(time):
    """ Convert CDF_EPOCH16 to CDF_EPOCH. """
    time = asarray(time)
    _epoch16_to_epoch = lambda a, b: lib.epoch16_to_epoch((a, b))
    return vectorize(_epoch16_to_epoch)(time[..., 0], time[..., 1])


def cdf_tt2000_to_epoch(time):
    """ Convert CDF_TIME_TT2000 to CDF_EPOCH. """
    return vectorize(lib.tt2000_to_epoch)(time)


def cdf_time_subset(cdf, start, stop, fields, margin=0, time_field='time'):
    """ Extract subset of the listed `fields` from a CDF data file.
    The extracted range of values match times which lie within the given
    closed time interval. The time interval is defined by the MDJ2000 `start`
    and `stop` values.
    The `margin` parameter is used to extend the index range by N surrounding
    elements. Negative margin is allowed.
    """
    if not fields:
        return [] # skip the data extraction for an empty variable list

    idx_start, idx_stop = array_slice(
        cdf.raw_var(time_field)[:], start, stop, margin
    )
    return [
        (field, cdf.raw_var(field)[idx_start:idx_stop]) for field in fields
    ]


def cdf_time_interp(cdf, time, fields, min_len=2, time_field='time',
                    nodata=None, types=None, bounds=None, **interp1d_prm):
    """ Read values of the listed fields from the CDF file and interpolate
    them at the given time values (the `time` array of MDJ2000 values).
    The data exceeding the time interval of the source data is filled with the
    `nodata` dictionary. The function accepts additional keyword arguments which
    are passed to the `scipy.interpolate.interp1d` interpolation (e.g., `kind`).
    """
    nodata = nodata or {}
    types = types or {}

    if not fields:
        return [] # skip the data extraction for an empty variable list

    # additional interpolation parameters
    if scipy.__version__ >= '0.14':
        interp1d_prm['assume_sorted'] = True
    interp1d_prm['copy'] = False
    interp1d_prm['bounds_error'] = False

    cdf_time = cdf.raw_var(time_field)[:]

    # if possible get subset of the time data
    if time.size > 0 and cdf_time.shape[0] > min_len:
        start, stop = bounds if bounds else (time.min(), time.max())
        slice_obj = slice(*array_slice(cdf_time, start, stop, min_len//2))
        cdf_time = cdf_time[slice_obj]
    else:
        slice_obj = Ellipsis

    # check minimal length required by the chosen kind of interpolation
    if time.size > 0 and cdf_time.shape[0] >= min_len:
        return [
            (field, data.astype(type_) if type_ else data)
            for field, data, type_ in (
                (
                    field,
                    interp1d(
                        cdf_time, cdf[field][slice_obj],
                        fill_value=nodata.get(field, nan), **interp1d_prm
                    )(time),
                    types.get(field)
                ) for field in fields
            )
        ]
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
