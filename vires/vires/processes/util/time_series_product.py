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
# pylint: disable=too-many-locals, too-many-arguments

from logging import getLogger, LoggerAdapter
from datetime import timedelta
from numpy import empty
from eoxserver.backends.access import connect
from vires.util import between_co
from vires.cdf_util import (
    cdf_open, datetime_to_cdf_rawtime, cdf_rawtime_to_datetime,
    timedelta_to_cdf_rawtime, CDF_EPOCH_TYPE,
)
from vires.models import Product, ProductCollection
from vires.dataset import Dataset
from .time_series import TimeSeries

VARIABLE_TRANSLATES = {
    "SWARM_EEF": {
        'Timestamp': 'timestamp',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    },
    "AUX_IMF_2_": {
        'Timestamp': 'Epoch',
        'IMF_BY_GSM': 'BY_GSM',
        'IMF_BZ_GSM': 'BZ_GSM',
    }
}


class ProductTimeSeries(TimeSeries):
    """ Product time-series class. """
    TIME_VARIABLE = "Timestamp"
    TIME_TOLERANCE = timedelta(microseconds=10) # time selection tolerance
    TIME_OVERLAP = timedelta(seconds=60) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(seconds=30) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=0.5)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["collection_id"], msg), kwargs

    def __init__(self, collection, logger=None):
        if isinstance(collection, basestring):
            collection = ProductCollection.objects.get(identifier=collection)
        variable_translate = VARIABLE_TRANSLATES.get(collection.range_type.name, {})
        self.translate_fw = variable_translate
        self.translate_bw = dict((v, k) for k, v in variable_translate.iteritems())
        self.collection = collection
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "collection_id": collection.identifier,
        })

        self.product_set = set() # stores all recorded source products

        # default segment neighbourhood
        self.segment_neighbourhood = self.TIME_SEGMENT_NEIGHBOURHOOD

    @property
    def products(self):
        """ Get list of all accessed products. """
        return list(self.product_set)

    @property
    def variables(self):
        return [
            self.translate_bw.get(band.identifier, band.identifier)
            for band in self.collection.range_type
        ]

    def _extract_dataset(self, product, extracted_variables, idx_low, idx_high):
        """ Extract dataset from a product. """
        dataset = Dataset()
        with cdf_open(connect(product.data_items.all()[0])) as cdf:
            for variable in extracted_variables:
                cdf_var = cdf.raw_var(self.translate_fw.get(variable, variable))
                if len(cdf_var.shape) > 0: # regular vector variable
                    data = cdf_var[idx_low:idx_high]
                else: # NRV scalar variable
                    data = empty(max(0, idx_high - idx_low), dtype=cdf_var.dtype)
                    data.fill(cdf_var[...])
                dataset.set(variable, data, cdf_var.type(), cdf_var.attrs)
        return dataset

    def _get_empty_dataset(self, variables):
        """ Get empty dataset. """
        self.logger.debug("empty dataset")
        self.logger.debug("extracted variables %s", variables)

        try:
            # we need need at least one product from the collection
            # to initialize correctly the empty variables
            product = Product.objects.filter(
                collections=self.collection
            ).order_by('begin_time')[0]
        except IndexError:
            self.logger.warning(
                "Empty collection! The variable types cannot be determined!"
            )
            return Dataset()
        else:
            # generate an empty dataset from the sample product
            self.logger.debug("template product: %s ", product.identifier)
            return self._extract_dataset(product, variables, 0, 0)

    def _subset_qs(self, start, stop):
        """ Subset Django query set. """
        return Product.objects.filter(
            collections=self.collection,
            begin_time__lt=(stop + self.TIME_TOLERANCE),
            end_time__gte=(start - self.TIME_TOLERANCE),
        )

    def subset_count(self, start, stop):
        """ Count matched number of products. """
        return self._subset_qs(start, stop).count()

    def subset(self, start, stop, variables=None):
        variables = self.get_extracted_variables(variables)
        self.logger.debug("subset: %s %s", start, stop)
        self.logger.debug("extracted variables %s", variables)

        if len(variables) == 0: # stop here if no variable is requested
            return

        counter = 0
        for product in self._subset_qs(start, stop).order_by('begin_time'):
            self.logger.debug("product: %s ", product.identifier)

            self.product_set.add(product.identifier) # record source product

            with cdf_open(connect(product.data_items.all()[0])) as cdf:
                # temporal sub-setting
                temp_var = cdf.raw_var(
                    self.translate_fw.get(self.TIME_VARIABLE, self.TIME_VARIABLE)
                )
                times, time_type = temp_var[:], temp_var.type()

                self.logger.debug(
                    "product time span %s %s",
                    cdf_rawtime_to_datetime(times.min(), time_type),
                    cdf_rawtime_to_datetime(times.max(), time_type),
                )

                time_idx = between_co(
                    times, datetime_to_cdf_rawtime(start, time_type),
                    datetime_to_cdf_rawtime(stop, time_type),
                ).nonzero()[0]

                low = time_idx.min() if time_idx.size else 0
                high = time_idx.max() + 1 if time_idx.size else 0

                self.logger.debug("product slice %s:%s", low, high)

                dataset = self._extract_dataset(product, variables, low, high)

            self.logger.debug("dataset length: %s ", dataset.length)

            yield dataset
            counter += 1

        # try to yield at least one empty dataset for a non-empty collection
        if counter < 1:
            dataset = self._get_empty_dataset(variables)
            if dataset:
                yield dataset

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=CDF_EPOCH_TYPE, valid_only=False):
        # TODO: support for different CDF time types
        if cdf_type != CDF_EPOCH_TYPE:
            raise TypeError("Unsupported CDF time type %r !" % cdf_type)

        variables = self.get_extracted_variables(variables)
        self.logger.debug("interpolated variables %s", variables)
        if len(variables) == 0: # stop here if no variable is requested
            return Dataset()

        if len(times) == 0: # return an empty dataset
            return self._get_empty_dataset(variables)

        # get the time bounds
        start, stop = min(times), max(times)

        # load the source interpolated data
        dataset_iterator = self.subset(
            cdf_rawtime_to_datetime(start, cdf_type) - self.TIME_OVERLAP,
            cdf_rawtime_to_datetime(stop, cdf_type) + self.TIME_OVERLAP,
            [self.TIME_VARIABLE] + variables,
        )

        self.logger.debug(
            "requested time-span [%s, %s]",
            cdf_rawtime_to_datetime(start, cdf_type),
            cdf_rawtime_to_datetime(stop, cdf_type)
        )
        self.logger.debug("requested dataset length %s", len(times))

        dataset = Dataset()
        for item in dataset_iterator:
            if item and item.length > 0:
                _times = item[self.TIME_VARIABLE]
                self.logger.debug(
                    "item time-span [%s, %s]",
                    cdf_rawtime_to_datetime(_times.min(), cdf_type),
                    cdf_rawtime_to_datetime(_times.max(), cdf_type),
                )
            else:
                self.logger.debug("item time-span is empty")
            dataset.append(item)

        if dataset and dataset.length > 0:
            _times = dataset[self.TIME_VARIABLE]
            self.logger.debug(
                "interpolated time-span %s, %s",
                cdf_rawtime_to_datetime(_times.min(), cdf_type),
                cdf_rawtime_to_datetime(_times.max(), cdf_type),
            )
        else:
            self.logger.debug("interpolated time-span is empty")

        self.logger.debug("interpolated dataset length: %s ", dataset.length)

        # TODO: handle the interpolation kinds
        return dataset.interpolate(
            times, self.TIME_VARIABLE, variables, {},
            gap_threshold=timedelta_to_cdf_rawtime(
                self.TIME_GAP_THRESHOLD, cdf_type
            ),
            segment_neighbourhood=timedelta_to_cdf_rawtime(
                self.segment_neighbourhood, cdf_type
            )
        )
