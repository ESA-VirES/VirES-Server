#-------------------------------------------------------------------------------
#
# CDF_EPOCH time conversion utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2015-2023 EOX IT Services GmbH
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

from datetime import datetime, timedelta
from numpy import empty, asarray, datetime64, isnat, nan, isnan
from vires.time_util import utc_to_naive

DT_MIN = datetime(1, 1, 1)
DT_MAX = datetime(9999, 12, 31, 23, 59, 59, 999999)
DT_INVALID_VALUE = datetime(9999, 12, 31, 23, 59, 59, 999999)
DT_EPOCH_2000 = datetime(2000, 1, 1)
DT_EPOCH_1970 = datetime(1970, 1, 1)


CDF_EPOCH_INVALID_VALUE = -1.0e31
CDF_EPOCH_PADDING_VALUE = 0.0

CDF_EPOCH_1970 = 62167219200000
CDF_EPOCH_2000 = 63113904000000

SECONDS_PER_DAY = 60 * 60 * 24
SECONDS_PER_MILLISECOND = 1e-3
MILLISECONDS_PER_MICROSECOND = 1e-3
MILLISECONDS_PER_SECOND = 1000
MICROSECONDS_PER_MILLISECOND = 1000
MILLISECONDS_PER_DAY = MILLISECONDS_PER_SECOND * SECONDS_PER_DAY
DAYS_PER_MILLISECOND = SECONDS_PER_MILLISECOND / SECONDS_PER_DAY


DT64_NAT = datetime64("NaT")

CDF_EPOCH_DT_LOWER_BOUND = 31622400000.000000
CDF_EPOCH_DT_UPPER_BOUND = 315538070400000.000000

#CDF_EPOCH_DT64_US_LOWER_BOUND =
#CDF_EPOCH_DT64_US_UPPER_BOUND =
#CDF_EPOCH_DT64_MS_LOWER_BOUND =
#CDF_EPOCH_DT64_MS_UPPER_BOUND =


def milliseconds_to_timedelta(delta_ms):
    """ Convert milliseconds to `datetime.timedelta` object.
    """
    return timedelta(microseconds=(delta_ms * MICROSECONDS_PER_MILLISECOND))


def timedelta_to_milliseconds(delta):
    """ Convert `datetime.timedelta` object to milliseconds.
    """
    return delta.total_seconds() * MILLISECONDS_PER_SECOND


def utc_datetime_to_cdf_epoch(dtobj):
    """ Convert datetime.datetime object to CDF_EPOCH.
    """
    if dtobj == DT_INVALID_VALUE:
        return CDF_EPOCH_INVALID_VALUE

    dtobj = utc_to_naive(dtobj)

    return timedelta_to_milliseconds(dtobj - DT_EPOCH_2000) + CDF_EPOCH_2000


def cdf_epoch_to_utc_datetime(epoch):
    """ Convert CDF_EPOCH values to datetime.datetime object.
    """
    if epoch < CDF_EPOCH_DT_LOWER_BOUND or epoch >= CDF_EPOCH_DT_UPPER_BOUND:
        # selects CDF_EPOCH_INVALID_VALUE and CDF_EPOCH_PADDING_VALUE
        return DT_INVALID_VALUE

    return milliseconds_to_timedelta(epoch - CDF_EPOCH_2000) + DT_EPOCH_2000


def cdf_epoch_to_utc_datetime64_us(epoch):
    """ Convert CDF_EPOCH to UTC numpy.datetime64[us] values.

    The datetime[us] covers large portion of the EPOCH with sub-milliseconds
    precision.
    """
    epoch = asarray(epoch)

    mask_invalid = (epoch == CDF_EPOCH_INVALID_VALUE)
    mask_valid = ~mask_invalid

    dt64 = empty(epoch.shape, "datetime64[us]")
    dt64[mask_invalid] = DT64_NAT

    valid_epoch = epoch[mask_valid]
    epoch1970_ms = (valid_epoch // 1).astype("int64") - CDF_EPOCH_1970
    epoch_frac_us = ((valid_epoch % 1) * MICROSECONDS_PER_MILLISECOND).astype("int64")

    dt64[mask_valid] = (
        epoch1970_ms * MICROSECONDS_PER_MILLISECOND + epoch_frac_us
    )

    return dt64


def utc_datetime64_us_to_cdf_epoch(dt64):
    """ Convert UTC numpy.datetime64[us] to CDF_EPOCH.
    """
    dt64 = asarray(dt64)

    mask_invalid = isnat(dt64)
    mask_valid = ~mask_invalid

    epoch = empty(dt64.shape, "float64")
    epoch[mask_invalid] = CDF_EPOCH_INVALID_VALUE

    # to preserve the exact millisecond boundaries, the calculation splits
    # the whole number of milliseconds from the remaining millisecond fractures

    utc1970us = dt64[mask_valid].astype("datetime64[us]").astype("int64")

    epoch_int = utc1970us // MICROSECONDS_PER_MILLISECOND + CDF_EPOCH_1970
    reminder = utc1970us % MICROSECONDS_PER_MILLISECOND

    epoch[mask_valid] = epoch_int + reminder * MILLISECONDS_PER_MICROSECOND

    return epoch


def cdf_epoch_to_utc_datetime64_ms(epoch):
    """ Convert CDF_EPOCH to UTC numpy.datetime64[ms] values.

    The datetime64[ms] covers huge portion of the EPOCH with milliseconds
    precision.
    """
    epoch = asarray(epoch)

    mask_invalid = (epoch == CDF_EPOCH_INVALID_VALUE)
    mask_valid = ~mask_invalid

    dt64 = empty(epoch.shape, "datetime64[ms]")
    dt64[mask_invalid] = DT64_NAT
    dt64[mask_valid] = (epoch[mask_valid] // 1).astype("int64") - CDF_EPOCH_1970

    return dt64


def utc_datetime64_ms_to_cdf_epoch(dt64):
    """ Convert UTC numpy.datetime64[ms] to CDF_EPOCH.
    """
    dt64 = asarray(dt64)

    mask_invalid = isnat(dt64)
    mask_valid = ~mask_invalid

    epoch = empty(dt64.shape, "float64")
    epoch[mask_invalid] = CDF_EPOCH_INVALID_VALUE

    utc1970ms = dt64[mask_valid].astype("datetime64[ms]").astype("int64")

    epoch[mask_valid] = utc1970ms + CDF_EPOCH_1970

    return epoch


def cdf_epoch_to_unix_epoch(epoch):
    """ Convert CDF_EPOCH to the Unix epoch (seconds since 1970-01-01).
    """
    epoch = asarray(epoch)

    mask_invalid = (
        (epoch == CDF_EPOCH_INVALID_VALUE) |
        (epoch == CDF_EPOCH_PADDING_VALUE)
    )
    mask_valid = ~mask_invalid

    unix_epoch = empty(epoch.shape, "float64")
    unix_epoch[mask_invalid] = nan

    unix_epoch[mask_valid] = (
        epoch[mask_valid] - CDF_EPOCH_1970
    ) * SECONDS_PER_MILLISECOND

    return unix_epoch


def cdf_epoch_to_mjd2000(epoch):
    """ Convert CDF_EPOCH to UTC-based MJD2000
    """
    epoch = asarray(epoch)

    mask_invalid = (
        (epoch == CDF_EPOCH_INVALID_VALUE) |
        (epoch == CDF_EPOCH_PADDING_VALUE)
    )
    mask_valid = ~mask_invalid

    mjd2000 = empty(epoch.shape, "float64")
    mjd2000[mask_invalid] = nan

    mjd2000[mask_valid] = (
        epoch[mask_valid] - CDF_EPOCH_2000
    ) * DAYS_PER_MILLISECOND

    return mjd2000


def mjd2000_to_cdf_epoch(mjd2000):
    """ Convert UTC-based MJD2000 to CDF_EPOCH
    """
    mjd2000 = asarray(mjd2000)

    mask_invalid = isnan(mjd2000)
    mask_valid = ~mask_invalid

    epoch = empty(mjd2000.shape, "float64")
    epoch[mask_invalid] = CDF_EPOCH_INVALID_VALUE

    # to preserve the exact day boundaries, the calculation splits
    # the whole number of days from the remaining day fractures

    epoch[mask_valid] = (
        mjd2000[mask_valid] * MILLISECONDS_PER_DAY + CDF_EPOCH_2000
    )

    return epoch
