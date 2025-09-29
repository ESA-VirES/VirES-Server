#-------------------------------------------------------------------------------
#
# Merged time data source - use to merge time-lines from multiple time-series
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

from numpy import argsort, concatenate
from .base import TimeSeries


class MergedTimeSeries(TimeSeries):
    """ Special time-series merging times from multiple time-series.

    This time-series is meant to provide only the merged time and other
    common variables and it is not meant to be used as an interpolated slave.
    """
    @property
    def collection_identifier(self):
        """ Get collection identifier. """
        return "-"

    @property
    def metadata(self):
        """ Get collection metadata. """
        return self.ts_sources[0].metadata

    @property
    def variables(self):
        return [self.time_variable, *self._variables]

    @property
    def essential_variables(self):
        return [self.time_variable, *self._essential_variables]

    @property
    def required_variables(self):
        raise NotImplementedError

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=TimeSeries.TIMESTAMP_TYPE, valid_only=False):
        raise NotImplementedError

    @property
    def products(self):
        merged_product_set = set()
        for ts_source in self.ts_sources:
            merged_product_set.update(ts_source.product_set)
        return list(merged_product_set)

    def __init__(self, ts_sources, **kwargs):
        super(). __init__(**kwargs)
        assert len(ts_sources) > 0
        self.ts_sources = ts_sources

        # extract common offered and essential variables and check time variable
        head, *tail = ts_sources
        variables = set(head.variables).difference([head.time_variable])
        essential_variables = (
            set(head.essential_variables).difference([head.time_variable])
        )

        for item in tail:
            if head.time_variable != item.time_variable:
                raise ValueError(
                    "Dataset time variable mismatch!"
                    f" {head.time_variable} != {item.time_variable}"
                )
            variables &= set(item.variables).difference([item.time_variable])
            essential_variables = (
                set(item.essential_variables).difference([item.time_variable])
            )
        self.time_variable = head.time_variable
        self._variables = list(variables)
        self._essential_variables = list(essential_variables)

    def subset(self, start, stop, variables=None):
        variables = self.get_extracted_variables(variables)
        if not variables:
            return
        yield from _MultisourceMerge([
            ts_source.subset(start, stop, variables)
            for ts_source in self.ts_sources
        ], self.time_variable, _DatasetWrapper)


class _DatasetWrapper:

    def __init__(self, dataset, time_variable):
        self.dataset = dataset
        self.time_variable = time_variable

    @property
    def empty(self):
        """ True for an empty dataset. """
        return self.dataset.is_empty

    @property
    def times(self):
        """ Extract times from the dataset. """
        return self.dataset[self.time_variable]

    @property
    def start(self):
        """ Get dataset start time. """
        return self.times.min()

    @property
    def end(self):
        """ Get dataset end time. """
        return self.times.max()

    @classmethod
    def merge(cls, items):
        """ Merge datasets """
        head, *tail = items
        for item in tail:
            head.dataset.append(item.dataset, remove_incompatible=True)
        index = argsort(head.times)
        if index.size > 1:
            # unique elements only
            dtimes = head.times[index[1:]] - head.times[index[:-1]]
            index = concatenate((index[:1], index[1:][dtimes > 0]))
        return head.dataset.subset(index)

    def split(self, cut_at):
        """ Split dataset into two at the given time. """
        mask = self.times <= cut_at
        if mask.all():
            return self, None
        if not mask.any():
            return None, self
        return (
            self.__class__(self.dataset.subset(mask), self.time_variable),
            self.__class__(self.dataset.subset(~mask), self.time_variable)
        )

class _MultisourceMerge:

    class _Source:

        def _get_next(self):
            while True:
                try:
                    item = self._wrapper_class(
                        next(self._iterator), self.time_variable
                    )
                except StopIteration:
                    return None
                if not item.empty:
                    return item

        def __init__(self, items, time_variable, wrapper_class):
            self._iterator = iter(items)
            self._wrapper_class = wrapper_class
            self.time_variable = time_variable
            self.head = self._get_next()

        def split_head(self, cut_at):
            """ Split the head item at the given value. """
            if self.head is None:
                return None
            head, tail = self.head.split(cut_at)
            if tail is None:
                self.head = self._get_next()
            elif head is not None:
                self.head = tail
            return head

        @property
        def empty(self):
            """ True if the source iterator is empty. """
            return self.head is None

    def __init__(self, sources, time_variable, wrapper_class):
        self._wrapper_class = wrapper_class
        self._sources = [
            self._Source(source, time_variable, wrapper_class)
            for source in sources
        ]

    def __iter__(self):
        return self

    def __next__(self):
        ends = [source.head.end for source in self._sources if source.head]
        if not ends:
            raise StopIteration
        cut_at = min(ends)
        items = [
            item for source in self._sources
            if (item := source.split_head(cut_at)) is not None
        ]
        return self._wrapper_class.merge(items)
