#-------------------------------------------------------------------------------
#
# Conjunctions utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=missing-module-docstring,too-many-arguments

from collections import namedtuple
from itertools import chain
from bisect import bisect_left, bisect_right
from numpy import concatenate, empty, searchsorted
from ..exceptions import DataIntegrityError


class OrderedIntervalsContainer():
    """ Ordered intervals container. """

    def verify(self):
        """ Verify integrity of the content. """
        if len(self) != len(self.starts) or len(self) != len(self.ends):
            raise DataIntegrityError("Data size mismatch.")

        for start, end, item in zip(
                self.starts, self.ends, self.items
            ):
            if start > end:
                raise DataIntegrityError(
                    "%s start %s after %s end %s" % (item, start, item, end)
                )
        for end_before, start_after, item_before, item_after in zip(
                self.ends[:-1], self.starts[1:], self.items[:-1], self.items[1:],
            ):
            if end_before > start_after:
                raise DataIntegrityError(
                    "%s end %s after %s start %s" % (
                        item_before, end_before,
                        item_after, start_after
                    )
                )

    def __len__(self):
        return len(self.items)

    def __init__(self, starts=None, ends=None, items=None):
        if starts is None or ends is None or items is None:
            starts, ends, items = [], [], []
        self.starts = starts
        self.ends = ends
        self.items = items

    def __iter__(self):
        yield from zip(self.starts, self.ends, self.items)

    def __getitem__(self, selection):
        if isinstance(selection, (slice, type(Ellipsis))): # subset selection
            return self.__class__(
                self.starts[selection],
                self.ends[selection],
                self.items[selection],
            )
        return (
            self.starts[selection],
            self.ends[selection],
            self.items[selection],
        )

    def join_and_update(self, *args):
        """ Concatenate input object and update itself."""
        self.starts = list(chain.from_iterable(arg.starts for arg in args))
        self.ends = list(chain.from_iterable(arg.ends for arg in args))
        self.items = list(chain.from_iterable(arg.items for arg in args))

    def remove(self, start, end):
        """ Remove items matched by the given time interval. """
        idx_start = bisect_left(self.ends, start)
        idx_end = bisect_right(self.starts, end)
        removed = self[idx_start:idx_end]
        self.join_and_update(
            self[:idx_start],
            self[idx_end:],
        )
        return removed

    def insert(self, start, end, item):
        """ Insert new item removing any previous content. """
        idx_start = bisect_left(self.ends, start)
        idx_end = bisect_right(self.starts, end)
        removed = self[idx_start:idx_end]
        self.join_and_update(
            self[:idx_start],
            self.__class__([start], [end], [item]),
            self[idx_end:],
        )
        return removed

    def __str__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join([str(self.starts), str(self.ends), str(self.items)]),
        )

    def __repr__(self):
        return str(self)


class InputData(namedtuple("InputData", ["times", "lats", "lons"])):
    """ Input data container class. """

    @classmethod
    def join(cls, *args):
        """ Concatenate tuple of lists. """
        return cls(*_join_data(args, concatenate))

    def __getitem__(self, selection):
        if isinstance(selection, int):
            return super().__getitem__(selection)
        return self.__class__(*tuple(item[selection] for item in self))


class OutputData(namedtuple("OutputData", ["times", "dists"])):
    """ Output data container class. """

    def verify(self, rtol=1e-6):
        """ Verify integrity of the content. """
        if self.times.shape != self.dists.shape:
            raise DataIntegrityError("Data size mismatch.")

        if (self.times[1:] < self.times[:-1]).any():
            raise DataIntegrityError("Times are not ordered.")

        if (self.times[1:] == self.times[:-1]).any():
            raise DataIntegrityError("Duplicate times found.")

        if ((self.dists < 0 - rtol) | (self.dists > 180 + rtol)).any():
            raise DataIntegrityError("Data range exceeded.")

    def __new__(cls, *args):
        if not args:
            args = (
                empty(0, 'datetime64[ms]'),
                empty(0, 'float64'),
            )
        return super(OutputData, cls).__new__(cls, *args)

    @property
    def is_empty(self):
        """ True if empty. """
        return self.times.size == 0

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
            data=self.times,
            start=start,
            end=end,
            left_closed=left_closed,
            right_closed=right_closed,
            margin=margin,
        )]

    def dump(self, prefix=""):
        """ Dump content to stdout. """
        for time, adist in zip(*self):
            print(prefix, time, "%6.3f" % adist)


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
