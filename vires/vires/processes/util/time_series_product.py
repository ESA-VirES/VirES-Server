#-------------------------------------------------------------------------------
#
# Data Source - product time-series class
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=too-many-locals

from logging import getLogger, LoggerAdapter
from datetime import timedelta
from eoxserver.backends.access import connect
from vires.util import include, between
from vires.cdf_util import (
    cdf_open, datetime_to_cdf_rawtime, cdf_rawtime_to_datetime,
    CDF_EPOCH_TYPE,
)
from vires.models import Product
from .dataset import Dataset
from .time_series import TimeSeries


class ProductTimeSeries(TimeSeries):
    """ Product time-series class. """
    TIME_VARIABLE = "Timestamp"
    TIME_TOLERANCE = timedelta(microseconds=10) # time selection tolerance
    TIME_OVERLAP = timedelta(seconds=60) # time interpolation overlap

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["collection_id"], msg), kwargs

    def __init__(self, collection, logger=None):
        self.collection = collection
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "collection_id": collection.identifier,
        })

    @property
    def variables(self):
        return [band.identifier for band in self.collection.range_type]

    def subset(self, start, stop, variables=None, subsampler=None):
        products_qs = Product.objects.filter(
            collections=self.collection,
            begin_time__lte=(stop + self.TIME_TOLERANCE),
            end_time__gte=(start - self.TIME_TOLERANCE),
        ).order_by('begin_time')

        self.logger.debug("subset: %s %s", start, stop)

        extracted_variables = None
        for product in products_qs:

            self.logger.debug("product: %s ", product.identifier)

            with cdf_open(connect(product.data_items.all()[0])) as cdf:

                # temporal sub-setting
                temp_var = cdf.raw_var(self.TIME_VARIABLE)
                times, time_type = temp_var[:], temp_var.type()

                self.logger.debug(
                    "product time span %s %s",
                    cdf_rawtime_to_datetime(times.min(), time_type),
                    cdf_rawtime_to_datetime(times.max(), time_type),
                )

                time_idx = between(
                    times, datetime_to_cdf_rawtime(start, time_type),
                    datetime_to_cdf_rawtime(stop, time_type),
                ).nonzero()[0]
                low = time_idx.min() if time_idx.size else 0
                high = time_idx.max() + 1 if time_idx.size else 0

                self.logger.debug("product slice %s:%s", low, high)

                # sub-sampling
                if subsampler:
                    subset_idx = subsampler(times[low:high], time_type)
                else:
                    subset_idx = None

                # prepare list of variables
                if variables is None:
                    extracted_variables = list(cdf) # get all available variables
                else:
                    # get applicable subset of the requested variables
                    extracted_variables = list(include(variables, cdf))

                self.logger.debug("extracted variables %s", extracted_variables)

                # extract data
                dataset = Dataset()
                for variable in extracted_variables:
                    cdf_var = cdf.raw_var(variable)
                    data = cdf_var[low:high]
                    if subset_idx is not None:
                        data = data[subset_idx]
                    dataset.set(variable, data, cdf_var.type())

            self.logger.debug("dataset length: %s ", dataset.length)

            yield dataset

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=CDF_EPOCH_TYPE, valid_only=False):
        # TODO: support for different CDF time types
        if cdf_type != CDF_EPOCH_TYPE:
            raise TypeError("Unsupported CDF time type %r !" % cdf_type)

        # get the time bounds
        start, stop = min(times), max(times)

        # load the source interpolated data
        dataset_iterator = self.subset(
            cdf_rawtime_to_datetime(start, cdf_type) - self.TIME_OVERLAP,
            cdf_rawtime_to_datetime(stop, cdf_type) + self.TIME_OVERLAP,
            None if variables is None else
            [self.TIME_VARIABLE] + list(variables),
        )

        self.logger.debug(
            "requested time-span %s, %s",
            cdf_rawtime_to_datetime(start, cdf_type),
            cdf_rawtime_to_datetime(stop, cdf_type)
        )
        self.logger.debug("requested dataset length %s", len(times))

        dataset = Dataset()
        for item in dataset_iterator:
            if item:
                self.logger.debug(
                    "item time-span %s, %s",
                    cdf_rawtime_to_datetime(item[self.TIME_VARIABLE].min(), cdf_type),
                    cdf_rawtime_to_datetime(item[self.TIME_VARIABLE].max(), cdf_type),
                )
            dataset.append(item)

        if dataset:
            self.logger.debug(
                "interpolated time-span %s, %s",
                cdf_rawtime_to_datetime(dataset[self.TIME_VARIABLE].min(), cdf_type),
                cdf_rawtime_to_datetime(dataset[self.TIME_VARIABLE].max(), cdf_type),
            )

        self.logger.debug("interpolated dataset length: %s ", dataset.length)

        # TODO: handle the interpolation kinds
        return dataset.interpolate(times, self.TIME_VARIABLE, variables, {})
