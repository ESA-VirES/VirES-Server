#-------------------------------------------------------------------------------
#
#  Various time handling utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=missing-docstring

import re
from datetime import datetime, timedelta
from django.utils.timezone import utc
from django.utils.dateparse import parse_datetime

RE_ZULU = re.compile(r'\+00:00$')

RE_ISO_8601_DURATION = re.compile(
    r"^(?P<sign>[+-])?P"
    r"(?:(?P<years>\d+(\.\d+)?)Y)?"
    r"(?:(?P<months>\d+(\.\d+)?)M)?"
    r"(?:(?P<days>\d+(\.\d+)?)D)?"
    r"T?(?:(?P<hours>\d+(\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(\.\d+)?)S)?$"
)


def format_datetime(dtobj):
    """ Convert datetime to an ISO-8601 date/time string. """
    return dtobj if dtobj is None else RE_ZULU.sub('Z', dtobj.isoformat('T'))


def parse_duration(value):
    ''' Parses an ISO 8601 duration string into a python timedelta object.
    Raises a `ValueError` if the conversion was not possible.
    '''
    if isinstance(value, timedelta):
        return value

    match = RE_ISO_8601_DURATION.match(value)
    if not match:
        raise ValueError(
            "Could not parse ISO 8601 duration from '%s'." % value
        )
    match = match.groupdict()

    sign = -1 if match['sign'] == '-' else 1
    days = float(match['days'] or 0)
    days += float(match['months'] or 0) * 30  # ?!
    days += float(match['years'] or 0) * 365  # ?!
    fsec = float(match['seconds'] or 0)
    fsec += float(match['minutes'] or 0) * 60
    fsec += float(match['hours'] or 0) * 3600

    if sign < 0:
        raise ValueError('Duration %s must not be negative!' % value)

    return timedelta(days, fsec)


def parse_datetime_or_duration(value, now=None):
    """ Parse input time specification provided either as ISO timestamp
    or relative ISO duration.
    """
    if value is None:
        return None
    datetime_ = parse_datetime(value)
    if datetime_ is not None:
        return naive_to_utc(datetime_)
    try:
        return naive_to_utc((now or datetime.utcnow()) + parse_duration(value))
    except ValueError:
        pass
    raise ValueError("Invalid time specification '%s'." % value)


def naive_to_utc(dt_obj):
    """ Convert naive `datetime.datetime` to UTC time-zone aware one. """
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=utc)
    return dt_obj.astimezone(utc)
