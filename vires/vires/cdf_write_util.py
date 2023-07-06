#-------------------------------------------------------------------------------
#
# CDF write utilities
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

from numpy import dtype
from .cdf_util import (
    CDF_EPOCH_TYPE,
    CDF_CHAR_TYPE,
    CDF_INT1_TYPE,
    CDF_INT2_TYPE,
    CDF_INT4_TYPE,
    CDF_INT8_TYPE,
    CDF_UINT1_TYPE,
    CDF_UINT2_TYPE,
    CDF_UINT4_TYPE,
    CDF_DOUBLE_TYPE,
    CDF_FLOAT_TYPE,
    cdf_rawtime_to_datetime64, datetime64_to_cdf_rawtime,
)

_TYPE_MAP = {
    dtype("int8"): CDF_INT1_TYPE,
    dtype("int16"): CDF_INT2_TYPE,
    dtype("int32"): CDF_INT4_TYPE,
    dtype("int64"): CDF_INT8_TYPE,
    dtype("uint8"): CDF_UINT1_TYPE,
    dtype("uint16"): CDF_UINT2_TYPE,
    dtype("uint32"): CDF_UINT4_TYPE,
    dtype("float64"): CDF_DOUBLE_TYPE,
    dtype("float32"): CDF_FLOAT_TYPE,
    dtype("datetime64[s]"): CDF_EPOCH_TYPE,
    dtype("datetime64[ms]"): CDF_EPOCH_TYPE,
    dtype("datetime64[us]"): CDF_EPOCH_TYPE,
}


def cdf_assert_backward_compatible_dtype(data):
    """ Assert backward compatible data type. """
    if data.dtype in (dtype("int64"), dtype("uint64")):
        raise TypeError("64bit integer types not supported!")


def cdf_add_variable(cdf, variable, data, attrs=None, **options):
    """ Add a new CDF variable to a CDF file. """
    cdf_type = get_cdf_type(data.dtype)
    data_converter = get_converter(cdf_type)
    cdf.new(
        variable, data_converter.encode(data),
        cdf_type, dims=data.shape[1:],
        **options
    )
    if attrs:
        cdf[variable].attrs.update(attrs)


def get_cdf_type(array_dtype):
    """ Get CDF datatype matched by the given numpy array dtype. """
    try:
        return _TYPE_MAP[array_dtype]
    except KeyError:
        pass

    if array_dtype.kind in ("S", "U"):
        return CDF_CHAR_TYPE

    raise TypeError("Array type %s not supported!" % array_dtype)


class CdfTypeDummy():
    """ CDF dummy type conversions. """

    @staticmethod
    def decode(values):
        """ Pass trough and do nothing. """
        return values

    @staticmethod
    def encode(values):
        """ Pass trough and do nothing. """
        return values


class CdfTypeEpoch():
    """ CDF Epoch Time type conversions. """

    @classmethod
    def decode(cls, cdf_raw_time):
        """ Convert CDF raw time to datetime64[ms]. """
        return cdf_rawtime_to_datetime64(cdf_raw_time, CDF_EPOCH_TYPE).astype("datetime64[ms]")

    @classmethod
    def encode(cls, time):
        """ Convert datetime64[*] to CDF raw time. """
        return datetime64_to_cdf_rawtime(time, CDF_EPOCH_TYPE)


def get_converter(cdf_type):
    """ Get CDF type converter. """
    return CdfTypeEpoch if cdf_type == CDF_EPOCH_TYPE else CdfTypeDummy
