#-------------------------------------------------------------------------------
#
# Data Source - base product time-series class
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
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

from logging import getLogger
from vires.util import pretty_list, LazyString
from vires.time_util import format_datetime
from vires.cdf_util import (
    cdf_rawtime_to_datetime, timedelta_to_cdf_rawtime, CDF_EPOCH_TYPE,
)
from vires.dataset import Dataset
from .base import TimeSeries


class BaseProductTimeSeries(TimeSeries):
    """ Base product time-series """

    def __init__(self, logger=None, **kwargs):
        super().__init__()
        self.logger = logger or getLogger(__name__)
        self.time_variable = kwargs.get("time_variable")
        self.time_tolerance = kwargs.get("time_tolerance")
        self.time_overlap = kwargs.get("time_overlap")
        self.time_gap_threshold = kwargs.get("time_gap_threshold")
        self.segment_neighbourhood = kwargs.get("segment_neighbourhood")
        self.interpolation_kinds = kwargs.get("interpolation_kinds")

    def _subset_qs(self, start, stop):
        """ Subset Django query set. """
        raise NotImplementedError

    def _subset(self, start, stop, variables):
        """ Get subset of the time series overlapping the given time range.
        """
        raise NotImplementedError

    def _subset_times(self, times, variables, cdf_type=TimeSeries.TIMESTAMP_TYPE):
        """ Get subset of the time series overlapping the given time array.
        """
        raise NotImplementedError

    def subset_count(self, start, stop):
        """ Count matched number of products. """
        return self._subset_qs(start, stop).count()

    def subset(self, start, stop, variables=None):
        variables = self.get_extracted_variables(variables)
        return iter(self._subset(start, stop, variables))

    def subset_times(self, times, variables=None, cdf_type=TimeSeries.TIMESTAMP_TYPE):
        """ Get subset of the time series overlapping the given time array.
        """
        variables = self.get_extracted_variables(variables)
        self.logger.debug("requested variables: %s", pretty_list(variables))
        return self._subset_times(times, variables, cdf_type)

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=TimeSeries.TIMESTAMP_TYPE, valid_only=False):

        variables = self.get_extracted_variables(variables)
        self.logger.debug("requested variables: %s", pretty_list(variables))

        if not variables:
            return Dataset()

        if self.time_variable not in variables:
            subset_variables = [self.time_variable] + variables
        else:
            subset_variables = variables

        dataset = self._subset_times(times, subset_variables, cdf_type)

        self.logger.debug("requested dataset length: %s", len(times))

        if not dataset.is_empty:
            _times = dataset[self.time_variable]
            self.logger.debug(
                "interpolated time-span: %s", LazyString(lambda: (
                f"{format_datetime(cdf_rawtime_to_datetime(_times.min(), cdf_type))}/"
                f"{format_datetime(cdf_rawtime_to_datetime(_times.max(), cdf_type))}"
            )))
        else:
            self.logger.debug("interpolated time-span is empty")

        self.logger.debug("interpolated dataset length: %s ", dataset.length)

        if dataset.is_empty:
            return dataset

        return dataset.interpolate(
            times, self.time_variable, variables,
            kinds=self.interpolation_kinds,
            gap_threshold=timedelta_to_cdf_rawtime(
                self.time_gap_threshold, cdf_type
            ),
            segment_neighbourhood=timedelta_to_cdf_rawtime(
                self.segment_neighbourhood, cdf_type
            )
        )
