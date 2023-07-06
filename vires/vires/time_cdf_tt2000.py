#-------------------------------------------------------------------------------
#
# CDF_TT2000 time conversion utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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
from numpy import asarray, empty, int64, datetime64, isnat, nan, isnan
from vires.time_util import utc_to_naive
from vires.leap_seconds import LEAP_NANOSECONDS_TABLE, LookupTable


SECONDS_PER_DAY = 60 * 60 * 24
SECONDS_PER_NANOSECOND = 1e-9
DAYS_PER_NANOSECOND = SECONDS_PER_NANOSECOND / SECONDS_PER_DAY
NANOSECONDS_PER_MICROSECOND = 1000
NANOSECONDS_PER_MILLISECOND = 1000000
NANOSECONDS_PER_SECOND = 1000000000
NANOSECONDS_PER_DAY = NANOSECONDS_PER_SECOND * SECONDS_PER_DAY
MICROSECONDS_PER_SECOND = 1000000
MICROSECONDS_PER_DAY = MICROSECONDS_PER_SECOND * SECONDS_PER_DAY
MILLISECONDS_PER_SECOND = 1000
MILLISECONDS_PER_DAY = MILLISECONDS_PER_SECOND * SECONDS_PER_DAY
MILLISECONDS_PER_NANOSECOND = 1e-6

CDF_EPOCH_2000 = 63113904000000
DT_EPOCH_2000 = datetime(2000, 1, 1)
DT_EPOCH_1970 = datetime(1970, 1, 1)
DAYS_UTC_2000_TO_1970_OFFSET = (DT_EPOCH_2000 - DT_EPOCH_1970).days
SEC_UTC_2000_TO_1970_OFFSET = DAYS_UTC_2000_TO_1970_OFFSET * SECONDS_PER_DAY
US_UTC_2000_TO_1970_OFFSET = DAYS_UTC_2000_TO_1970_OFFSET * MICROSECONDS_PER_DAY
NS_UTC_2000_TO_1970_OFFSET = DAYS_UTC_2000_TO_1970_OFFSET * NANOSECONDS_PER_DAY
NS_JD_TO_MJD_OFFSET = 43200000000000 # 12 hours JD (noon) to MJD (midnight) offset
NS_TT_TO_TAI_OFFSET = 32184000000 # 32.184 seconds TT to TAI offset
NS_TT2000_TO_TAI2000_OFFSET = NS_JD_TO_MJD_OFFSET - NS_TT_TO_TAI_OFFSET

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807

CDF_TT2000_INVALID_VALUE = INT64_MIN
CDF_TT2000_PADDING_VALUE = INT64_MIN + 1
CDF_TT2000_MIN_VALID = INT64_MIN + 2
CDF_TT2000_MAX_VALID = INT64_MAX
CDF_TT2000_DT64_US_LOWER_BOUND = -9223372036854775000 # 1707-09-22T12:12:10.961225
CDF_TT2000_DT64_US_UPPER_BOUND = 9223372036854775000 # 2262-04-11T23:47:16.854775
CDF_TT2000_DT64_NS_UPPER_BOUND = 8276644106038775807 # 2262-04-11T23:47:16.854775807

CDF_EPOCH_INVALID_VALUE = -1.0e31
CDF_EPOCH_PADDING_VALUE = 0.0
CDF_EPOCH_LOWER_BOUND = 53890575130961.226562500
CDF_EPOCH_UPPER_BOUND = 72337319167670.765625000

DT_INVALID_VALUE = datetime(9999, 12, 31, 23, 59, 59, 999999)
DT64_NAT = datetime64("NaT")

DT64_NS_MIN_VALID = datetime64(INT64_MIN + 1, "ns")
DT64_NS_MAX_VALID = datetime64(INT64_MAX, "ns")
DT64_NS_LOWER_BOUND = datetime64("1707-09-22T12:12:10.961224194", "ns")
DT64_NS_UPPER_BOUND = DT64_NS_MAX_VALID
DT64_US_LOWER_BOUND = datetime64("1707-09-22T12:12:10.961225", "us")
DT64_US_UPPER_BOUND = datetime64("2292-04-11T11:46:07.670775", "us")

MJD2000_LOWER_BOUND = -106751.491539800641476176679134
MJD2000_UPPER_BOUND = 106752.490366559897665865719318


def _create_custom_lookup_tables(table):
    """ Creating custom lookup table for the TT2000 conversions. """
    # Using lower precision for the UTC dates:
    # - leap seconds are always aligned to whole UTC days
    # - to prevent possible int64 overflows
    times_utc2000d = table.times_utc // NANOSECONDS_PER_DAY
    times_tt2000ns = table.times_tai - NS_TT2000_TO_TAI2000_OFFSET
    offset_tt2000_to_utc2000 = table.offsets_tai2utc - NS_TT2000_TO_TAI2000_OFFSET
    # fix lower bounds
    times_utc2000d[0] = table.times_utc[0]
    times_tt2000ns[0] = table.times_tai[0]

    return (
        LookupTable(times_utc2000d, offset_tt2000_to_utc2000),
        LookupTable(times_tt2000ns, offset_tt2000_to_utc2000)
    )

OFFSET_UTC2000, OFFSET_TT2000 = _create_custom_lookup_tables(LEAP_NANOSECONDS_TABLE)


def convert_tt2000_to_utc2000_ns(tt2000ns):
    """ Convert TT2000 time in integer nanoseconds since TT 2000-01-01T12:00
    to UTC integer nanoseconds since UTC 2000-01-01T00:00.

    In addition, the int64-overflow mask is returned.
    """
    utc2000ns = tt2000ns - OFFSET_TT2000(tt2000ns)
    overflow_mask = tt2000ns > utc2000ns
    return utc2000ns, overflow_mask


def convert_utc2000_to_tt2000_ns(utc2000ns):
    """ Convert UTC integer nanoseconds since UTC 2000-01-01T00:00
    to TT2000 time in integer nanoseconds since TT 2000-01-01T12:00

    In addition, the int64-underflow mask is returned.
    """
    tt2000ns =  utc2000ns + OFFSET_UTC2000(utc2000ns // NANOSECONDS_PER_DAY)
    underflow_mask = tt2000ns > utc2000ns
    return tt2000ns, underflow_mask


def cdf_tt2000_to_cdf_epoch(tt2000):
    """ Convert CDF_TT2000 to CDF_EPOCH values.
    """
    tt2000 = asarray(tt2000)

    mask_invalid = tt2000 == CDF_TT2000_INVALID_VALUE
    mask_padding = tt2000 == CDF_TT2000_PADDING_VALUE
    mask_valid = ~(mask_invalid | mask_padding)

    epoch = empty(tt2000.shape, "float64")
    epoch[mask_invalid] = CDF_EPOCH_INVALID_VALUE
    epoch[mask_padding] = CDF_EPOCH_PADDING_VALUE

    # to preserve the exact millisecond boundaries, the calculation splits
    # the whole number of milliseconds from the remaining millisecond fractures

    utc2000ns, mask_overflow = convert_tt2000_to_utc2000_ns(tt2000[mask_valid])

    # overflow handling - temporally subtract one day
    utc2000ns[mask_overflow] -= NANOSECONDS_PER_DAY
    epoch_int = utc2000ns // NANOSECONDS_PER_MILLISECOND + CDF_EPOCH_2000
    epoch_int[mask_overflow] += MILLISECONDS_PER_DAY
    reminder = utc2000ns % NANOSECONDS_PER_MILLISECOND

    epoch[mask_valid] = epoch_int + reminder * MILLISECONDS_PER_NANOSECOND

    return epoch


def cdf_epoch_to_cdf_tt2000(epoch):
    """ Convert CDF_EPOCH to CDF_TT2000 values.

    The conversion function does not truncate the CDF_EPOCH value to the whole
    milliseconds. If needed, this should be performed outside of this function.
    """
    epoch = asarray(epoch)

    mask_padding = epoch == CDF_EPOCH_PADDING_VALUE
    #mask_invalid = epoch == CDF_EPOCH_INVALID_VALUE # < CDF_EPOCH_UPPER_BOUND
    mask_invalid = (epoch < CDF_EPOCH_LOWER_BOUND) | (epoch > CDF_EPOCH_UPPER_BOUND)
    mask_valid = ~mask_invalid

    tt2000 = empty(epoch.shape, "int64")
    tt2000[mask_invalid] = CDF_TT2000_INVALID_VALUE
    tt2000[mask_padding] = CDF_TT2000_PADDING_VALUE

    # to preserve the exact millisecond boundaries, the calculation splits
    # the whole number of milliseconds from the remaining millisecond fractures

    valid_epoch = epoch[mask_valid]
    epoch2000_ms = (valid_epoch // 1).astype("int64") - CDF_EPOCH_2000
    epoch_frac_ns = ((valid_epoch % 1) * NANOSECONDS_PER_MILLISECOND).astype("int64")
    offset_ns = OFFSET_UTC2000(epoch2000_ms // MILLISECONDS_PER_DAY)

    tt2000[mask_valid] = (
        epoch2000_ms * NANOSECONDS_PER_MILLISECOND + epoch_frac_ns + offset_ns
    )

    return tt2000


def timedelta_to_nanoseconds(delta):
    """ Convert datetime.timedelta to nanoseconds. """
    return (
        delta.days * NANOSECONDS_PER_DAY +
        delta.seconds * NANOSECONDS_PER_SECOND +
        delta.microseconds * NANOSECONDS_PER_MICROSECOND
    )


def nanoseconds_to_timedelta(delta_ns):
    """ Convert nanoseconds to datetime.timedelta. """
    return timedelta(
        microseconds=(delta_ns // NANOSECONDS_PER_MICROSECOND)
    )


def cdf_tt2000_to_utc_datetime(tt2000):
    """ Convert CDF_TT2000 to UTC datetime.datetime object
    """
    if tt2000 in (CDF_TT2000_INVALID_VALUE, CDF_TT2000_PADDING_VALUE):
        return DT_INVALID_VALUE

    # Python integer does not overflow.
    utc2000 = int(tt2000) - int(OFFSET_TT2000(tt2000))

    return DT_EPOCH_2000 + nanoseconds_to_timedelta(utc2000)


def utc_datetime_to_cdf_tt2000(dtobj):
    """ Convert UTC datetime.datetime object to CDF_TT2000
    """
    if dtobj == DT_INVALID_VALUE:
        return int64(CDF_TT2000_INVALID_VALUE)

    dtobj = utc_to_naive(dtobj)

    utc2000ns = timedelta_to_nanoseconds(dtobj - DT_EPOCH_2000)
    offset_ns = int(OFFSET_UTC2000(int(utc2000ns // NANOSECONDS_PER_DAY)))

    tt2000ns = utc2000ns + offset_ns

    is_invalid = (
        (tt2000ns < CDF_TT2000_MIN_VALID) or (tt2000ns > CDF_TT2000_MAX_VALID)
    )
    if is_invalid:
        return int64(CDF_TT2000_INVALID_VALUE)

    return int64(tt2000ns)


def cdf_tt2000_to_utc_datetime64_ns(tt2000):
    """ Convert CDF_TT2000 to UTC numpy.datetime64[ns] values.

    The datetime[ns] type can keep TT2000 values without a loss of the precision
    though, due to the base on 1970-01-01, the range of the covered dates
    is shorter by ~30 years (up to UTC 2262-04-11T23:47:16.854775807).
    """
    tt2000 = asarray(tt2000)

    mask_invalid = (
        (tt2000 == CDF_TT2000_INVALID_VALUE) |
        (tt2000 == CDF_TT2000_PADDING_VALUE) |
        (tt2000 > CDF_TT2000_DT64_NS_UPPER_BOUND)
    )
    mask_valid = ~mask_invalid

    dt64 = empty(tt2000.shape, "datetime64[ns]")
    dt64[mask_invalid] = DT64_NAT

    tt2000_valid = tt2000[mask_valid]
    dt64[mask_valid] = (
        tt2000_valid - OFFSET_TT2000(tt2000_valid) + NS_UTC_2000_TO_1970_OFFSET
    ).astype("datetime64[ns]")

    return dt64


def utc_datetime64_ns_to_cdf_tt2000(dt64):
    """ Convert UTC numpy.datetime64[ns] values to CDF TT2000.

    The datetime[ns] type can keep TT2000 values without lost of the precision
    though, due to the base on 1970-01-01, the range of the covered dates
    is shorter by ~30 years (up to UTC 2262-04-11T23:47:16.854775807).
    """
    dt64 = asarray(dt64)
    mask_invalid = (
        isnat(dt64) |
        (dt64 < DT64_NS_LOWER_BOUND) |
        (dt64 > DT64_NS_UPPER_BOUND)
    )
    mask_valid = ~mask_invalid

    tt2000 = empty(dt64.shape, "int64")
    tt2000[mask_invalid] = CDF_TT2000_INVALID_VALUE

    utc1970ns = dt64[mask_valid].astype("datetime64[ns]").astype("int64")
    offsets_ns = OFFSET_UTC2000(
        utc1970ns // NANOSECONDS_PER_DAY - DAYS_UTC_2000_TO_1970_OFFSET
    ) - NS_UTC_2000_TO_1970_OFFSET
    tt2000[mask_valid] = utc1970ns + offsets_ns

    return tt2000


def cdf_tt2000_to_utc_datetime64_us(tt2000):
    """ Convert CDF_TT2000 to UTC numpy.datetime64[us] values.

    The datetime[us] covers the whole range of TT2000 at cost of truncating the
    precision to microseconds.
    """
    tt2000 = asarray(tt2000)

    mask_invalid = (
        (tt2000 == CDF_TT2000_INVALID_VALUE) |
        (tt2000 == CDF_TT2000_PADDING_VALUE)
    )
    mask_valid = ~mask_invalid

    dt64 = empty(tt2000.shape, "datetime64[us]")
    dt64[mask_invalid] = DT64_NAT

    tt2000ns = tt2000[mask_valid]
    dt64[mask_valid] = (
        tt2000ns // NANOSECONDS_PER_MICROSECOND
        - OFFSET_TT2000(tt2000ns) // NANOSECONDS_PER_MICROSECOND
        + US_UTC_2000_TO_1970_OFFSET
    )

    return dt64


def utc_datetime64_us_to_cdf_tt2000(dt64):
    """ Convert UTC numpy.datetime64[us] values to CDF TT2000.

    The datetime[us] covers the whole range of TT2000 at cost of truncating the
    precision to microseconds.
    """
    dt64 = asarray(dt64)
    mask_invalid = (
        isnat(dt64) | (dt64 < DT64_US_LOWER_BOUND) | (dt64 > DT64_US_UPPER_BOUND)
    )
    mask_valid = ~mask_invalid

    tt2000 = empty(dt64.shape, "int64")
    tt2000[mask_invalid] = CDF_TT2000_INVALID_VALUE

    utc2000us = (
        dt64[mask_valid].astype("datetime64[us]").astype("int64")
        - US_UTC_2000_TO_1970_OFFSET
    )

    offsets_us = OFFSET_UTC2000(
        utc2000us // MICROSECONDS_PER_DAY
    ) // NANOSECONDS_PER_MICROSECOND

    tt2000[mask_valid] = (utc2000us + offsets_us) * NANOSECONDS_PER_MICROSECOND

    return tt2000


def cdf_tt2000_to_unix_epoch(tt2000):
    """ Convert CDF_TT2000 to Unix epoch (float number of seconds since
    1970-01-01, no leap seconds)
    """
    tt2000 = asarray(tt2000)

    mask_invalid = (
        (tt2000 == CDF_TT2000_INVALID_VALUE) |
        (tt2000 == CDF_TT2000_PADDING_VALUE)
    )
    mask_valid = ~mask_invalid

    unix_epoch = empty(tt2000.shape, "float64")
    unix_epoch[mask_invalid] = nan

    # to preserve exact second boundaries, the calculation splits
    # the whole number of seconds from the remaining second fractures

    # overflow handling - temporally subtract one day
    utc2000ns, mask_overflow = convert_tt2000_to_utc2000_ns(tt2000[mask_valid])
    utc2000ns[mask_overflow] -= NANOSECONDS_PER_DAY
    seconds = utc2000ns // NANOSECONDS_PER_SECOND + SEC_UTC_2000_TO_1970_OFFSET
    seconds[mask_overflow] += SECONDS_PER_DAY
    reminder = utc2000ns % NANOSECONDS_PER_SECOND

    unix_epoch[mask_valid] = seconds + reminder * SECONDS_PER_NANOSECOND

    return unix_epoch


def cdf_tt2000_to_mjd2000(tt2000):
    """ Convert CDF_TT2000 to UTC-based MJD2000
    """
    tt2000 = asarray(tt2000)

    mask_invalid = (
        (tt2000 == CDF_TT2000_INVALID_VALUE) |
        (tt2000 == CDF_TT2000_PADDING_VALUE)
    )
    mask_valid = ~mask_invalid

    mjd2000 = empty(tt2000.shape, "float64")
    mjd2000[mask_invalid] = nan

    # to preserve the exact day boundaries, the calculation splits
    # the whole number of days from the remaining day fractures

    utc2000ns = convert_tt2000_to_utc2000_ns(tt2000[mask_valid])

    # overflow handling - temporally subtract one day
    utc2000ns, mask_overflow = convert_tt2000_to_utc2000_ns(tt2000[mask_valid])
    utc2000ns[mask_overflow] -= NANOSECONDS_PER_DAY
    days = utc2000ns // NANOSECONDS_PER_DAY
    days[mask_overflow] += 1
    reminder = utc2000ns % NANOSECONDS_PER_DAY

    mjd2000[mask_valid] = days + reminder * DAYS_PER_NANOSECOND
    return mjd2000


def mjd2000_to_cdf_tt2000(mjd2000):
    """ Convert UTC-based MJD2000 to CDF_TT2000
    """
    mjd2000 = asarray(mjd2000)

    mask_invalid = (
        isnan(mjd2000) |
        (mjd2000 < MJD2000_LOWER_BOUND) |
        (mjd2000 > MJD2000_UPPER_BOUND)
    )
    mask_valid = ~mask_invalid

    tt2000 = empty(mjd2000.shape, "int64")
    tt2000[mask_invalid] = CDF_TT2000_INVALID_VALUE

    # to preserve the exact day boundaries, the calculation splits
    # the whole number of days from the remaining day fractures

    valid_mjd2000 = mjd2000[mask_valid]
    mjd2000_d = (valid_mjd2000 // 1).astype("int64")
    mjd_frac_ns = ((valid_mjd2000 % 1) * NANOSECONDS_PER_DAY).astype("int64")
    offset_ns = OFFSET_UTC2000(mjd2000_d)

    tt2000[mask_valid] = (
        mjd2000_d * NANOSECONDS_PER_DAY + mjd_frac_ns + offset_ns
    )

    return tt2000
