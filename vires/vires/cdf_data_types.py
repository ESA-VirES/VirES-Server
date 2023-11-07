#-------------------------------------------------------------------------------
#
# CDF data types
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
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
# pylint: disable=too-many-return-statements,consider-using-f-string

from numpy import dtype
from spacepy import pycdf
from .time_util import naive_to_utc, format_datetime

DT_OBJECT = dtype('object')
DT_FLOAT64 = dtype('float64')

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

CDF_TIME_TYPES = {CDF_EPOCH_TYPE, CDF_EPOCH16_TYPE, CDF_TIME_TT2000_TYPE}

CDF_TYPE_TO_LABEL = {
    CDF_EPOCH_TYPE: "CDF_EPOCH",
    CDF_EPOCH16_TYPE: "CDF_EPOCH16",
    CDF_TIME_TT2000_TYPE: "CDF_TIME_TT2000",
    CDF_FLOAT_TYPE: "CDF_FLOAT",
    CDF_DOUBLE_TYPE: "CDF_DOUBLE",
    CDF_REAL4_TYPE: "CDF_REAL4",
    CDF_REAL8_TYPE: "CDF_REAL8",
    CDF_UINT1_TYPE: "CDF_UINT1",
    CDF_UINT2_TYPE: "CDF_UINT2",
    CDF_UINT4_TYPE: "CDF_UINT4",
    CDF_INT1_TYPE: "CDF_INT1",
    CDF_INT2_TYPE: "CDF_INT2",
    CDF_INT4_TYPE: "CDF_INT4",
    CDF_INT8_TYPE: "CDF_INT8",
    CDF_CHAR_TYPE: "CDF_CHAR",
}

CDF_TYPE_MAP = {
    CDF_REAL4_TYPE: CDF_FLOAT_TYPE,
    CDF_REAL8_TYPE: CDF_DOUBLE_TYPE,
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


def cdf_type_map(cdf_type):
    """ CDF type conversion. """
    return CDF_TYPE_MAP.get(cdf_type, cdf_type)


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
                return "{%s}" % ";".join(value_formater(value) for value in arr)
            return formater
        if cdf_type == CDF_DOUBLE_TYPE:
            return lambda v: "%.9g" % v
        if cdf_type == CDF_EPOCH_TYPE:
            if dtype == DT_FLOAT64:
                return lambda v: "%.14g" % v
            if dtype == DT_OBJECT:
                return lambda v: format_datetime(naive_to_utc(v))
            return str
        if cdf_type == CDF_CHAR_TYPE:
            return lambda v: v.decode('utf-8')
        return str
    return _get_formater(data.shape, data.dtype, cdf_type)
