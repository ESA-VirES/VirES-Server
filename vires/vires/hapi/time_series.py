#-------------------------------------------------------------------------------
#
# VirES HAPI - time-series reader
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
# pylint: disable=missing-docstring,unused-argument,too-few-public-methods
# pylint: disable=too-few-public-methods,too-many-arguments

from logging import getLogger, LoggerAdapter
from vires.time_util import naive_to_utc, format_datetime
from vires.models import Product
from .readers import CdfTimeSeriesReader


class TimeSeries():
    """ Product time-series class. """

    @staticmethod
    def _get_id(base_id, dataset_id, default_dataset_id):
        if dataset_id and dataset_id == default_dataset_id:
            return "%s:%s" % (base_id, dataset_id)
        return base_id

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["collection_id"], msg), kwargs

    def __init__(self, collection, dataset_id, logger=None):
        default_dataset_id = collection.type.default_dataset_id
        self.collection = collection
        self.dataset_id = dataset_id or default_dataset_id
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "collection_id": self._get_id(
                collection.identifier, dataset_id, default_dataset_id
            ),
        })

    def subset(self, start, stop, parameters):
        return _TimeSeriesSubsetIterator(
            self.collection, self.dataset_id,
            start, stop, parameters, logger=self.logger,
        )


class _TimeSeriesSubsetIterator():
    """ Time-series subset iterator yielding datasets objects.  """

    def __iter__(self):
        return self._items

    def __init__(self, collection, dataset_id, start, stop, parameters, logger):
        self.logger = logger

        self.sources = set()

        self.logger.debug("subset: %s/%s", format_datetime(start), format_datetime(stop))
        self.logger.debug("extracted parameters: %s", ", ".join(parameters.keys()))

        time_parameter, time_parameter_options = self._find_timestamp(parameters)

        self._items = self._read_data(
            self._query(collection, naive_to_utc(start), naive_to_utc(stop)),
            dataset_id,
            CdfTimeSeriesReader(
                start, stop, parameters,
                time_parameter=time_parameter,
                time_parameter_options=time_parameter_options,
            )
        )

    @staticmethod
    def _find_timestamp(parameters):
        for name, details in parameters.items():
            if details.get('primaryTimestamp'):
                return name, details
        raise ValueError("Primary time-stamp not found!")

    @staticmethod
    def _query(collection, start, stop):
        """ Subset Django query set. """
        return Product.objects.prefetch_related('collection__type').filter(
            collection=collection,
            begin_time__lt=stop,
            end_time__gte=start,
            begin_time__gte=(start - collection.max_product_duration),
        )

    def _read_data(self, query, dataset_id, reader):
        """ Yield extracted products' subsets. """
        for product in query:
            source_dataset = product.get_dataset(dataset_id)
            if source_dataset:
                self.sources.add(product.identifier)
                yield from reader(source_dataset)
