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
GZIP_COMPRESSION_LEVEL2 = ctypes.c_long(2)
GZIP_COMPRESSION_LEVEL3 = ctypes.c_long(3)
GZIP_COMPRESSION_LEVEL4 = ctypes.c_long(4)
GZIP_COMPRESSION_LEVEL5 = ctypes.c_long(5)
GZIP_COMPRESSION_LEVEL6 = ctypes.c_long(6)
GZIP_COMPRESSION_LEVEL7 = ctypes.c_long(7)
GZIP_COMPRESSION_LEVEL8 = ctypes.c_long(8)
GZIP_COMPRESSION_LEVEL9 = ctypes.c_long(9)

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


def get_cdf_data_reader(cdf):
    """ Create CDF data reader. """
    def read_cdf_data(variable, slice_=None):
        """ Read data from a CDF file. """
        return cdf.raw_var(variable)[slice_ or Ellipsis]
    return read_cdf_data
