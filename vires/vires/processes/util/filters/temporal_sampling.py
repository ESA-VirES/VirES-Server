#-------------------------------------------------------------------------------
#
# Data filters - temporal sampling
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

from logging import getLogger, LoggerAdapter
from numpy import empty, diff, concatenate, in1d, arange, inf
from vires.interpolate import Interp1D
from .base import Filter
from .utils import merge_indices


class MinStepSampler(Filter):
    """ Filter class sub-sampling the dataset so that the distance
    between two neighbours is not shorter than the requested minimal step.
    """
    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'min-step-sampler %s: %s' % (
                self.extra["variable"], msg
            ), kwargs

    def __init__(self, variable, min_step, base_value=None, logger=None):
        self.variable = variable
        self.min_step = min_step
        self.base_value = base_value
        self.logger = self._LoggerAdapter(
            logger or getLogger(__name__), {"variable": self.variable}
        )

    @property
    def required_variables(self):
        return (self.variable,)

    def filter(self, dataset, index=None):
        if index is None:
            return self._filter(dataset[self.variable])
        return index[self._filter(dataset[self.variable][index])]

    def _filter(self, data):
        """ Low-level sub-sampling filter. """
        min_step = self.min_step
        base_value = self.base_value
        if data.size > 0: # non-empty array
            if base_value is None:
                base_value = data[0]
            self.logger.debug("min.step: %s, base value: %s", min_step, base_value)
            self.logger.debug("initial size: %d", data.size)
            index = concatenate(
                ([1], diff(((data - base_value) / self.min_step).astype('int')))
            ).nonzero()[0]
        else: # empty array
            index = empty(0, 'int64')
        self.logger.debug("filtered size: %d", index.size)
        return index

    def __str__(self):
        return "%s: MinStepSampler(%r, %r)" % (
            self.variable, self.min_step, self.base_value
        )


class GroupingSampler(Filter):
    """ Filter class sub-sampling the dataset so that the distance
    between two neighbour groups is not shorter than the requested minimal step.
    """
    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'grouping-sampler %s: %s' % (
                self.extra["variable"], msg
            ), kwargs

    def __init__(self, variable, logger=None):
        self.variable = variable
        self.logger = self._LoggerAdapter(
            logger or getLogger(__name__), {"variable": self.variable}
        )

    @property
    def required_variables(self):
        return (self.variable,)

    def filter(self, dataset, index=None):
        if index is None:
            return arange(dataset.length)
        return self._filter(dataset[self.variable], index)

    def _filter(self, data, index):
        """ Sampler to get possible additional values which have the same
        variable value.
        """
        if data.size > 0: # non-empty array
            self.logger.debug("initial size: %d", data.size)
            res_index = in1d(data, data[index]).nonzero()[0]
        else: # empty array
            res_index = empty(0, 'int64')
        self.logger.debug("filtered size: %d", index.size)
        return res_index

    def __str__(self):
        return "%s: GroupingSampler()" % self.variable


class ExtraSampler(Filter):
    """ Add extra samples to contain points of the second time-series. """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'extra-sampler %s %s: %s' % (
                self.extra["label"], self.extra["variable"], msg
            ), kwargs

    def __init__(self, variable, label, time_series, logger=None):
        self.variable = variable
        self.label = label
        self.time_series = time_series
        self.logger = self._LoggerAdapter(
            logger or getLogger(__name__),
            {"variable": self.variable, "label": self.label}
        )

    @property
    def required_variables(self):
        return (self.variable,)

    def filter(self, dataset, index=None):
        return merge_indices(index, self._filter(dataset[self.variable]))

    def _filter(self, data):
        """ Sampler to add additional sample from the extra time-series. """
        gap_threshold = inf
        segment_neighbourhood = 0

        dataset = self.time_series.subset_times(data, [self.variable])

        if dataset.length == 0:
            return empty(0, 'int64')

        _, _, index = Interp1D(
            data, dataset[self.variable], gap_threshold, segment_neighbourhood
        ).indices_nearest

        return index

    def __str__(self):
        return "%s: ExtraSampler(%s)" % (self.variable, self.label)
