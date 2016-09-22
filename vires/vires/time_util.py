#
# Time utilities.
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
# pylint: disable=too-few-public-methods

import math
import time
from datetime import datetime, timedelta
from django.utils.dateparse import utc

DT_1970 = datetime(1970, 1, 1)
DT_2000 = datetime(2000, 1, 1)

TZ_UTC = utc

def timedelta_to_iso_duration(tdobj):
    """ Convert `datetime.timedelta` object to ISO-8601 duration string. """
    days = "%dD" % tdobj.days if tdobj.days != 0 else ""
    if tdobj.microseconds != 0:
        seconds = "T%fS" % (tdobj.seconds + 1e-6 * tdobj.microseconds)
    elif tdobj.seconds != 0 or tdobj.days == 0:
        seconds = "T%dS" % tdobj.seconds
    else:
        seconds = ""
    return "P%s%s" % (days, seconds)


def datetime_mean(start, stop):
    """ Get arithmetic mean of two `datetime.datetime` values. """
    return (stop - start)/2 + start


def naive_to_utc(dt_obj):
    """ Convert naive `datetime.datetime` to UTC time-zone aware one. """
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=TZ_UTC)
    return dt_obj


def utc_to_naive(dt_obj):
    """ Convert naive `datetime.datetime` to UTC time-zone aware one. """
    if dt_obj.tzinfo:
        dt_obj = dt_obj.astimezone(TZ_UTC).replace(tzinfo=None)
    return dt_obj


def is_leap_year(year):
    """ Return boolean flag indicating whether the given year is a leap year
    or not.
    """
    if year > 1582:
        return year % 4 == 0 and year % 100 != 0 or year % 400 == 0
    else:
        return year % 4 == 0


def days_per_year(year):
    """ Return integer number of days in the given year."""
    return 365 + is_leap_year(year)


def time_to_seconds(hours=0, minutes=0, seconds=0, microseconds=0):
    """ Convert time to number of seconds. """
    return 1e-6*microseconds + seconds + 60*(minutes + 60*hours)


def time_to_day_fraction(hours=0, minutes=0, seconds=0, microseconds=0):
    """ Convert time since midnight to date fraction. """
    return time_to_seconds(hours, minutes, seconds, microseconds) / 86400.0


def day_fraction_to_time(fraction):
    """ Convert day fraction to to time as (hour, min, sec, usec) tuple. """
    subsec, sec = math.modf(round(fraction * 86400.0, 6)) # round to usec
    sec, usec = int(sec), int(subsec * 1e6)
    min_, sec = sec / 60, sec % 60,
    hour, min_ = min_ / 60, min_ % 60,
    return hour, min_, sec, usec


def day2k_to_date(day2k):
    """ Convert integer day number since 2000-01-01 to date as (year, month, day)
    tuple.
    """
    # ref: https://en.wikipedia.org/wiki/Julian_day#Julian_or_Gregorian_calendar_from_Julian_day_number
    # Gregorian date formula applied since 1582-10-15
    # Julian date formula applied until 1582-10-04
    d__ = int(day2k) + 2451545
    f__ = d__ + 1401 # Julian calender
    if d__ > 2299160: # Gregorian calender
        f__ += (((4*d__ + 274277)//146097)*3)//4 - 38
    e__ = 4*f__ + 3
    h__ = 5*((e__ % 1461)//4) + 2
    day = (h__%153)//5 + 1
    month = (h__//153 + 2)%12 + 1
    year = e__//1461 - 4716 + (14 - month)//12
    return year, month, day


def day2k_to_year(day2k):
    """ Convert integer day number since 2000-01-01 to date as (year, month, day)
    tuple.
    """
    # ref: https://en.wikipedia.org/wiki/Julian_day#Julian_or_Gregorian_calendar_from_Julian_day_number
    # Gregorian date formula applied since 1582-10-15
    # Julian date formula applied until 1582-10-04
    d__ = int(day2k) + 2451545
    f__ = d__ + 1401 # Julian calender
    if d__ > 2299160: # Gregorian calender
        f__ += (((4*d__ + 274277)//146097)*3)//4 - 38
    e__ = 4*f__ + 3
    h__ = 5*((e__ % 1461)//4) + 2
    return e__//1461 - 4716 + (13 - (h__//153 + 2)%12)//12


def date_to_day2k(year, month, day):
    """ Convert date to number of days since 2000-01-01. """
    # ref: https://en.wikipedia.org/wiki/Julian_day#Converting_Julian_or_Gregorian_calendar_date_to_Julian_day_number
    # ref: http://www.cs.utsa.edu/~cs1063/projects/Spring2011/Project1/jdn-explanation.html
    # Gregorian date formula applied since 1582-10-05
    # Julian date formula applied until 1582-10-04
    a__ = (14 - month) // 12
    y__ = year + 4800 - a__
    m__ = month + 12*a__ - 3
    day2k = day + (153*m__ + 2)//5 + 365*y__ + y__//4 - 2483628
    if (year, month, day) > (1582, 10, 4):
        day2k += y__//400 - y__//100 + 38
    return day2k


def year_to_day2k(year):
    """ Get the date to number of days since 2000-01-01 of the year start. """
    y__ = year + 4799
    day2k = 365*y__ + y__//4 - 2483321
    if year > 1582:
        day2k += y__//400 - y__//100 + 38
    return day2k


def datetime_to_mjd2000(dt_obj):
    """ Convert `datetime.datetime` object to Modified Julian Date 2000. """
    dt_obj = utc_to_naive(dt_obj)
    day_fraction = time_to_day_fraction(
        dt_obj.hour, dt_obj.minute, dt_obj.second, dt_obj.microsecond
    )
    day2k = date_to_day2k(dt_obj.year, dt_obj.month, dt_obj.day)
    return day2k + day_fraction


def mjd2000_to_datetime(mjd2k):
    """ Convert Modified Julian Date 2000 to `datetime.datetime` object. """
    day2k = math.floor(mjd2k)
    year, month, day = day2k_to_date(day2k)
    hour, min_, sec, usec = day_fraction_to_time(mjd2k - day2k)
    return datetime(year, month, day, hour, min_, sec, usec)


def datetime_to_unix_epoch(dt_obj):
    """ Convert `datetime.datetime` object to number of UTC seconds since
    1970-01-01.
    """
    return (utc_to_naive(dt_obj) - DT_1970).total_seconds()


def unix_epoch_to_datetime(ux_epoch):
    """ Convert number of seconds since 1970-01-01 to `datetime.datetime`
    object.
    """
    return datetime.utcfromtimestamp(ux_epoch)
    #return timedelta(seconds=ux_epoch) + DT_1970


def unix_epoch_to_mjd2000(ux_epoch):
    """ Convert number of seconds since 1970-01-01 to Modified Julian Date 2000.
    """
    return (ux_epoch / 86400.0) - 10957.0


def mjd2000_to_unix_epoch(mjd2k):
    """ Convert number of seconds since 1970-01-01 to Modified Julian Date 2000.
    """
    return (mjd2k + 10957.0) * 86400.0


def datetime_to_decimal_year(dt_obj):
    """ Convert `datetime.datetime` object to year fraction. """
    dt_obj = utc_to_naive(dt_obj)
    d_fraction = time_to_day_fraction(
        dt_obj.hour, dt_obj.minute, dt_obj.second, dt_obj.microsecond
    )
    d_number = (
        date_to_day2k(dt_obj.year, dt_obj.month, dt_obj.day) -
        year_to_day2k(dt_obj.year)
    )
    return dt_obj.year + (d_number + d_fraction) / days_per_year(dt_obj.year)


def decimal_year_to_datetime(decimal_year):
    """ Convert decimal year to `datetime.datetime` object."""
    fraction, year = math.modf(decimal_year)
    year = int(year)
    days = fraction * days_per_year(year)
    year_start = datetime(year=year, month=1, day=1)
    return year_start + timedelta(days=days)


def mjd2000_to_decimal_year(mjd2k):
    """ Convert Modified Julian Date 2000 to decimal year. """
    year = day2k_to_year(int(math.floor(mjd2k)))
    return year + (mjd2k - year_to_day2k(year)) / days_per_year(year)


def decimal_year_to_mjd2000(decimal_year):
    """ Covert decimal year to Modified Julian Date 2000. """
    fraction, year = math.modf(decimal_year)
    year = int(year)
    return year_to_day2k(year) + fraction * days_per_year(year)


class Timer(object):
    """ Object used to measure elapsed time in seconds. """

    def __init__(self):
        self._start = None
        self.reset()

    def __call__(self):
        """ Get elapsed time in seconds."""
        return time.time() - self._start

    def reset(self):
        """ Reset initial time."""
        self._start = time.time()


