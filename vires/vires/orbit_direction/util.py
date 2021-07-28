#-------------------------------------------------------------------------------
#
# Orbit direction - update utilities
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
# pylint: disable=too-many-arguments

from collections import namedtuple
from itertools import chain
from numpy import concatenate, full, empty, searchsorted
from .common import (
    FLAG_START, FLAG_MIDDLE, FLAG_END,
    FLAG_ASCENDING, FLAG_DESCENDING, FLAG_UNDEFINED,
)

FLAG_TO_STR = {
    FLAG_START: "START",
    FLAG_END: "END",
    FLAG_MIDDLE: "",
}

ODIR_TO_STR = {
    FLAG_ASCENDING: "A",
    FLAG_DESCENDING: "D",
    FLAG_UNDEFINED: "?"
}


class Products(namedtuple("Products", ["names", "start_times", "end_times"])):
    """ Product list container class. """

    def __new__(cls, *args):
        if not args:
            args = [], [], []
        return super(Products, cls).__new__(cls, *args)

    @classmethod
    def join(cls, *args):
        """ Concatenate tuple of lists. """
        return cls(*_join_data(args, lambda l: list(chain.from_iterable(l))))

    def __getitem__(self, selection):
        if  isinstance(selection, int):
            return super().__getitem__(selection)
        return self.__class__(*tuple(item[selection] for item in self))


class InputData(namedtuple("InputData", ["times", "lats", "lons", "rads"])):
    """ Input data container class. """

    @classmethod
    def join(cls, *args):
        """ Concatenate tuple of lists. """
        return cls(*_join_data(args, concatenate))


class OutputData(namedtuple("OutputData", ["times", "odirs", "flags"])):
    """ Output data container class. """

    def __new__(cls, *args):
        if not args:
            args = (
                empty(0, 'datetime64[ms]'),
                empty(0, 'int8'),
                empty(0, 'int8')
            )
        return super(OutputData, cls).__new__(cls, *args)

    @property
    def is_empty(self):
        return self.times.size == 0

    @classmethod
    def get_start(cls, time, odir):
        """ Build the segment start output data sequence. """
        return cls([time], [odir], [FLAG_START])

    @classmethod
    def get_end(cls, time, odir=FLAG_UNDEFINED):
        """ Build the segment end output data sequence. """
        return cls([time], [odir], [FLAG_END])

    @classmethod
    def get_body(cls, times, odirs):
        """ Build the segment body output data sequence. """
        return cls(times, odirs, full(times.shape, FLAG_MIDDLE, 'int8'))

    @classmethod
    def join(cls, *args):
        """ Concatenate tuple of lists. """
        return cls(*_join_data(args, concatenate))

    def __getitem__(self, selection):
        if isinstance(selection, int):
            return super().__getitem__(selection)
        return self.__class__(*tuple(item[selection] for item in self))

    def time_subset(self, start=None, end=None, left_closed=True,
                    right_closed=True, margin=0):
        """ Get temporal subset of the data. """
        return self[_sorted_range(
           data= self.times,
           start=start,
           end=end,
           left_closed=left_closed,
           right_closed=right_closed,
           margin=margin,
        )]

    def dump(self, prefix=""):
        """ Dump content to stdout. """
        for time, odir, flag in zip(*self):
            print(prefix, time, ODIR_TO_STR[odir], FLAG_TO_STR[flag])


def _sorted_range(data, start, end, left_closed=True, right_closed=True,
                 margin=0):
    """ Get a slice of a sorted data array matched by the given interval. """
    idx_start, idx_end = None, None

    if start is not None:
        idx_start = searchsorted(data, start, 'left' if left_closed else 'right')
        if margin > 0:
            idx_start = max(0, idx_start - margin)

    if end is not None:
        idx_end = searchsorted(data, end, 'right' if right_closed else 'left')
        if margin > 0:
            idx_end += margin

    return slice(idx_start, idx_end)


def _join_data(data_items, join_func):
    if not data_items:
        return ()
    accm = tuple([] for _ in data_items[0])
    for data_item in data_items:
        for idx, array_ in enumerate(data_item):
            accm[idx].append(array_)
    return tuple(join_func(list_item) for list_item in accm)
