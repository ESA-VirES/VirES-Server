#-------------------------------------------------------------------------------
#
#  Various utilities
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

from logging import LoggerAdapter
from datetime import datetime
from django.utils.timezone import utc
from django.utils.dateparse import parse_datetime
from eoxserver.core.util.timetools import parse_duration


def datetime_to_string(dtobj):
    """ Format datetime object. """
    return dtobj if dtobj is None else dtobj.isoformat('T')


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


class AccessLoggerAdapter(LoggerAdapter):
    """ Logger adapter adding extra fields required by the access logger. """

    def __init__(self, logger, username=None, remote_addr=None, **kwargs):
        super().__init__(logger, {
            "remote_addr": remote_addr if remote_addr else "-",
            "username": username if username else "-",
        })


def get_remote_addr(request):
    """ Extract remote address from the Django HttpRequest """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.partition(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_username(user):
    """ Extract username of the authenticated user or return None
    """
    return user.username if user and user.is_authenticated else None
