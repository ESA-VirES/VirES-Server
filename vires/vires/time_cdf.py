#-------------------------------------------------------------------------------
#
# CDF time time-conversions
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
# pylint: disable=

#TODO implement proper CDF_EPOCH16 handling.

from numpy import ndarray, asarray, vectorize
from spacepy import pycdf
from .cdf_data_types import (
    CDF_EPOCH_TYPE, CDF_EPOCH16_TYPE, CDF_TIME_TT2000_TYPE,
    CDF_TYPE_TO_LABEL,
)
from .time_cdf_epoch import (
    SECONDS_PER_MILLISECOND,
    MILLISECONDS_PER_SECOND,
    milliseconds_to_timedelta,
    timedelta_to_milliseconds,
    cdf_epoch_to_utc_datetime,
    utc_datetime_to_cdf_epoch,
    cdf_epoch_to_utc_datetime64_us,
    utc_datetime64_us_to_cdf_epoch,
    cdf_epoch_to_unix_epoch,
    cdf_epoch_to_mjd2000,
    mjd2000_to_cdf_epoch,
)
from .time_cdf_tt2000 import (
    SECONDS_PER_NANOSECOND,
    NANOSECONDS_PER_SECOND,
    timedelta_to_nanoseconds,
    nanoseconds_to_timedelta,
    cdf_tt2000_to_cdf_epoch,
    cdf_epoch_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime,
    utc_datetime_to_cdf_tt2000,
    cdf_tt2000_to_utc_datetime64_ns,
    utc_datetime64_ns_to_cdf_tt2000,
    cdf_tt2000_to_unix_epoch,
    cdf_tt2000_to_mjd2000,
    mjd2000_to_cdf_tt2000,
)


class UnsupportedCDFTimeTypeError(TypeError):
    """ Custom unsupported CDF time type error exception. """
    def __init__(self, cdf_type):
        if cdf_type in CDF_TYPE_TO_LABEL:
            type_str = f"{CDF_TYPE_TO_LABEL[cdf_type]} ({cdf_type})"
        else:
            type_str = f"{cdf_type}"
        super().__init__(f"Unsupported CDF time type {type_str}")
        self.cdf_type = cdf_type


def cdf_epoch16_to_cdf_epoch(time):
    """ Convert CDF_EPOCH16 to CDF_EPOCH. """
    time = asarray(time)
    _epoch16_to_epoch = lambda a, b: pycdf.lib.epoch16_to_epoch((a, b))
    return vectorize(_epoch16_to_epoch)(time[..., 0], time[..., 1])


RAW_CDF_TIMES_CONVERSION = {
    (CDF_EPOCH_TYPE, CDF_TIME_TT2000_TYPE): cdf_epoch_to_cdf_tt2000,
    (CDF_TIME_TT2000_TYPE, CDF_EPOCH_TYPE): cdf_tt2000_to_cdf_epoch,
    (CDF_EPOCH16_TYPE, CDF_EPOCH_TYPE): cdf_epoch16_to_cdf_epoch,
}

def convert_cdf_raw_times(cdf_raw_time, cdf_type_in, cdf_type_out):
    """ Covert between different raw CDF times.
    """
    if cdf_type_in == cdf_type_out:
        return cdf_raw_time
    try:
        convert = RAW_CDF_TIMES_CONVERSION[(cdf_type_in, cdf_type_out)]
    except KeyError:
        raise UnsupportedCDFTimeTypeError(cdf_type_out) from None
    return convert(cdf_raw_time)



def cdf_rawtime_to_datetime64(cdf_raw_time, cdf_type):
    """ Convert CDF raw time to numpy.datetime64. """
    if cdf_type == CDF_EPOCH_TYPE:
        return cdf_epoch_to_utc_datetime64_us(cdf_raw_time)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return cdf_tt2000_to_utc_datetime64_ns(cdf_raw_time)
    raise UnsupportedCDFTimeTypeError(cdf_type)


def datetime64_to_cdf_rawtime(time, cdf_type):
    """ Convert numpy.datetime64 to CDF raw-time. """
    if cdf_type == CDF_EPOCH_TYPE:
        return utc_datetime64_us_to_cdf_epoch(time)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return utc_datetime64_ns_to_cdf_tt2000(time)
    raise UnsupportedCDFTimeTypeError(cdf_type)


def cdf_rawtime_delta_in_seconds(raw_time1, raw_time2, cdf_type):
    """ Calculate difference between two raw CDF times converted to seconds.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return (raw_time1 - raw_time2) * SECONDS_PER_MILLISECOND
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return (raw_time1 - raw_time2) * SECONDS_PER_NANOSECOND
    raise UnsupportedCDFTimeTypeError(cdf_type)


def cdf_rawtime_subtract_delta_in_seconds(raw_time, delta_s, cdf_type):
    """ Subtract delta value in seconds from the given raw CDF time.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return raw_time - delta_s * MILLISECONDS_PER_SECOND
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return raw_time - (
            asarray(delta_s) * NANOSECONDS_PER_SECOND
        ).astype("int64")
    raise UnsupportedCDFTimeTypeError(cdf_type)


def cdf_rawtime_to_timedelta(raw_time_delta, cdf_type):
    """ Convert a CDF raw time difference to `datetime.timedelta` object.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return milliseconds_to_timedelta(raw_time_delta)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return nanoseconds_to_timedelta(raw_time_delta)
    raise UnsupportedCDFTimeTypeError(cdf_type)


def timedelta_to_cdf_rawtime(time_delta, cdf_type):
    """ Convert `datetime.timedelta` object to CDF raw time scale.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return timedelta_to_milliseconds(time_delta)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return timedelta_to_nanoseconds(time_delta)
    raise UnsupportedCDFTimeTypeError(cdf_type)


def datetime_to_cdf_rawtime(time, cdf_type):
    """ Convert `datetime.datetime` object to CDF raw time. """

    if cdf_type == CDF_EPOCH_TYPE:
        convert = utc_datetime_to_cdf_epoch
    elif cdf_type == CDF_TIME_TT2000_TYPE:
        convert = utc_datetime_to_cdf_tt2000
    else:
        raise UnsupportedCDFTimeTypeError(cdf_type)

    if isinstance(time, ndarray):
        convert = vectorize(convert, otypes=('float64',))

    return convert(time)


def cdf_rawtime_to_datetime(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to an array
    of `dateitme.datetime` objects.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        convert = cdf_epoch_to_utc_datetime
    elif cdf_type == CDF_TIME_TT2000_TYPE:
        convert = cdf_tt2000_to_utc_datetime
    else:
        raise UnsupportedCDFTimeTypeError(cdf_type)

    if isinstance(raw_time, ndarray):
        convert = vectorize(convert, otypes=('object',))

    return convert(raw_time)


def cdf_rawtime_to_unix_epoch(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to an array of Unix epoch values.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return cdf_epoch_to_unix_epoch(raw_time)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return cdf_tt2000_to_unix_epoch(raw_time)
    raise UnsupportedCDFTimeTypeError(cdf_type)


def cdf_rawtime_to_mjd2000(raw_time, cdf_type):
    """ Convert an array of CDF raw time values to array of MJD2000 values.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return cdf_epoch_to_mjd2000(raw_time)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return cdf_tt2000_to_mjd2000(raw_time)
    raise UnsupportedCDFTimeTypeError(cdf_type)


def mjd2000_to_cdf_rawtime(time, cdf_type):
    """ Convert an array of MJD2000 values to an array of CDF raw time values.
    """
    if cdf_type == CDF_EPOCH_TYPE:
        return mjd2000_to_cdf_epoch(time)
    if cdf_type == CDF_TIME_TT2000_TYPE:
        return mjd2000_to_cdf_tt2000(time)
    raise UnsupportedCDFTimeTypeError(cdf_type)
