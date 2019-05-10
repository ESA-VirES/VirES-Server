#-------------------------------------------------------------------------------
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Daniel Santillan <daniel.santillan@eox.at>
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
# pylint: disable=too-few-public-methods, too-many-arguments

from sys import exc_info
from traceback import extract_tb
from math import ceil, floor
from itertools import ifilter, ifilterfalse


try:
    from numpy import full
except ImportError:
    from numpy import empty
    def full(shape, value, dtype=None, order='C'):
        """ Numpy < 1.8 workaround. """
        arr = empty(shape, dtype, order)
        arr.fill(value)
        return arr


def format_exception():
    """ Custom exception formatting. """
    type_, exception, traceback_ = exc_info()
    filename, lineno, _, _ = extract_tb(traceback_)[-1]
    message = str(exception)
    return "%s:%s:%s%s" % (
        filename, lineno, type_.__name__,
        ": %s" % message if message else ""
    )


def unique(iterable):
    """ Remove duplicates from an iterable preserving the order."""
    items = set()
    for item in ifilterfalse(items.__contains__, iterable):
        yield item
        items.add(item)


def exclude(iterable, excluded):
    """ Remove items from the `iterable` which are present among the
    elements of the `excluded` set.
    """
    return ifilterfalse(set(excluded).__contains__, iterable)


def include(iterable, included):
    """ Remove items from the `iterable` which are not present among the
    elements of the `included` set.
    """
    return ifilter(set(included).__contains__, iterable)


class cached_property(object): #pylint: disable=invalid-name
    """ Decorator converting a given method with a single self argument
     into a property cached on the instance.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        value = self.func(instance)
        instance.__dict__[self.func.__name__] = value
        return value


def between(data, lower_bound, upper_bound):
    """ Get mask of values within the given closed interval:
        lower_bound <= value <= upper_bound
    """
    return (data >= lower_bound) & (data <= upper_bound)


def between_co(data, lower_bound, upper_bound):
    """ Get mask of values within the given closed-open interval:
        lower_bound <= value < upper_bound
    """
    return (data >= lower_bound) & (data < upper_bound)


# TODO: To be removed.
#       Unnecessary as the Python 2.6 compatibility has been dropped.
def get_total_seconds(td_obj):
    """ Get `datetime.timedelta` as total number of seconds. """
    try:
        return td_obj.total_seconds()
    except AttributeError:
        return td_obj.microseconds*1e-6 + td_obj.seconds + td_obj.days*86400


def float_array_slice(start, stop, first, last, step, tolerance):
    """
        Get array index range for given sub-setting interval
        (`start`, `stop`), extent of the array (`first`, `last`),
        step of the regular sampling `step`, and selection tolerance
        `tolerance`.
    """
    rstep = 1.0 / step
    _first = first * rstep
    _tolerance = abs(tolerance * rstep)
    size = 1 + int(round(rstep * last - _first))
    low = int(ceil(rstep * start - _tolerance - _first))
    high = int(floor(rstep * stop + _tolerance - _first))
    if high < 0 or low >= size:
        return 0, 0
    return max(0, low), min(size, high + 1)


def datetime_array_slice(start, stop, first, last, step, tolerance):
    """
        Get array index range for given sub-setting time interval
        (`start`, `stop`), time extent of the array (`first`, `last`),
        step of the regular time sampling `step`, and selection tolerance
        time `tolerance`.
    """
    return float_array_slice(
        (start - first).total_seconds(), (stop - first).total_seconds(),
        0.0, (last - first).total_seconds(),
        step.total_seconds(), tolerance.total_seconds()
    )
