#-------------------------------------------------------------------------------
#
# CDF file-format utilities
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2014-2023 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments,consider-using-f-string,unused-import

from os.path import exists
from datetime import datetime
import ctypes
from numpy import nan, full, searchsorted
import scipy
from scipy.interpolate import interp1d
import spacepy
from spacepy import pycdf
from spacepy.pycdf import CDFError
from . import FULL_PACKAGE_NAME
from .time_util import naive_to_utc, format_datetime
from .time_cdf import (
    UnsupportedCDFTimeTypeError,
    cdf_epoch16_to_cdf_epoch,
    convert_cdf_raw_times,
    cdf_rawtime_to_datetime64,
    datetime64_to_cdf_rawtime,
    cdf_rawtime_delta_in_seconds,
    cdf_rawtime_subtract_delta_in_seconds,
    cdf_rawtime_to_timedelta,
    timedelta_to_cdf_rawtime,
    datetime_to_cdf_rawtime,
    cdf_rawtime_to_datetime,
    cdf_rawtime_to_unix_epoch,
    cdf_rawtime_to_mjd2000,
    mjd2000_to_cdf_rawtime,
)
from .cdf_data_types import (
    CDF_EPOCH_TYPE,
    CDF_EPOCH16_TYPE,
    CDF_TIME_TT2000_TYPE,
    CDF_FLOAT_TYPE,
    CDF_DOUBLE_TYPE,
    CDF_REAL8_TYPE,
    CDF_REAL4_TYPE,
    CDF_UINT1_TYPE,
    CDF_UINT2_TYPE,
    CDF_UINT4_TYPE,
    CDF_INT1_TYPE,
    CDF_INT2_TYPE,
    CDF_INT4_TYPE,
    CDF_INT8_TYPE,
    CDF_CHAR_TYPE,
    CDF_TIME_TYPES,
    CDF_TYPE_TO_LABEL,
    CDF_TYPE_MAP,
    LABEL_TO_CDF_TYPE,
    CDF_TYPE_TO_DTYPE,
    cdf_type_map,
    get_formatter,
)

GZIP_COMPRESSION = pycdf.const.GZIP_COMPRESSION
GZIP_COMPRESSION_LEVEL1 = ctypes.c_long(1)

CDF_CREATOR = "%s [%s-%s, libcdf-%s]" % (
    FULL_PACKAGE_NAME, spacepy.__name__, spacepy.__version__,
    "%s.%s.%s-%s" % pycdf.lib.version
)


def is_cdf_file(filename):
    """ Test if file is supported CDF file. """
    try:
        with cdf_open(filename):
            return True
    except CDFError:
        return False


def cdf_open(filename, mode="r", backward_compatible=True):
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
            pycdf.lib.set_backward(backward_compatible)
            cdf = pycdf.CDF(filename, "")
            # add extra attributes
            cdf.attrs.update({
                "CREATOR": CDF_CREATOR,
                "CREATED": format_datetime(naive_to_utc(
                    datetime.utcnow().replace(microsecond=0)
                ))
            })
    else:
        raise ValueError("Invalid mode value %r!" % mode)
    return cdf


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
