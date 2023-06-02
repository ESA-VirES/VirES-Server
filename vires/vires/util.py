#-------------------------------------------------------------------------------
#
#  various utilities
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
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
from itertools import filterfalse


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
    for item in filterfalse(items.__contains__, iterable):
        yield item
        items.add(item)


def exclude(iterable, excluded):
    """ Remove items from the `iterable` which are present among the
    elements of the `excluded` set.
    """
    return filterfalse(set(excluded).__contains__, iterable)


def include(iterable, included):
    """ Remove items from the `iterable` which are not present among the
    elements of the `included` set.
    """
    return filter(set(included).__contains__, iterable)


class cached_property(): #pylint: disable=invalid-name
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


class AttributeDict(dict):
    """ A dictionary whose keys can be accessed as object attributes. """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class LazyString:
    """ Lazy string conversion. """

    def __init__(self, get_string):
        self.get_string = get_string

    def __str__(self):
        return self.get_string()


def pretty_list(items):
    """ Pretty list of strings output. """
    return ", ".join(items)
