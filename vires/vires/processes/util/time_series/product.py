#-------------------------------------------------------------------------------
#
# Data Source - product time-series class
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
# pylint: disable=too-few-public-methods,too-many-arguments,too-many-locals

from logging import getLogger, LoggerAdapter
from numpy import full
from vires.util import pretty_list, LazyString, cached_property
from vires.cdf_util import cdf_rawtime_to_datetime, CDF_UINT1_TYPE
from vires.time_util import naive_to_utc, format_datetime
from vires.dataset import Dataset
from .base import TimeSeries
from .base_product import BaseProductTimeSeries
from .data_extraction import CDFDataset


class ProductTimeSeries(BaseProductTimeSeries):
    """ Product time-series class. """
    COLLECTION_INDEX_VARIABLE = "DataSource"

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            collection_id = self.extra["collection_id"]
            return f"{collection_id}: {msg}", kwargs

    def __init__(self, source, logger=None):

        params = source.params

        super().__init__(
            source=source,
            logger=self._LoggerAdapter(logger or getLogger(__name__), {
                "collection_id": source.identifier,
            }),
            time_variable=source.time_variables[0],
            second_time_variable=(
                source.time_variables[1]
                if len(source.time_variables) > 1 else None
            ),
            time_tolerance=params.TIME_TOLERANCE,
            time_overlap=params.TIME_OVERLAP,
            time_gap_threshold=params.TIME_GAP_THRESHOLD,
            segment_neighbourhood=params.TIME_SEGMENT_NEIGHBOURHOOD,
            interpolation_kinds=params.VARIABLE_INTERPOLATION_KINDS,
        )

        self.source = source

    @property
    def metadata(self):
        """ Get collection metadata. """
        return self.source.metadata

    @property
    def collection_identifier(self):
        """ Get collection identifier. """
        return self.source.identifier

    @property
    def variables(self):
        variables = list(self.source.dataset_definition)
        if len(self.source.collections) > 1:
            variables.append(self.COLLECTION_INDEX_VARIABLE)
        return variables

    def subset_count(self, start, stop):
        """ Count products overlapping the given time interval. """
        return self.source.count_products(start, stop, self.time_tolerance)

    def _subset_times(self, times, variables, cdf_type=TimeSeries.TIMESTAMP_TYPE):
        """ Get subset of the time series overlapping the given time array.
        """
        def _format_time_range(start, stop):
            return (
                f"{format_datetime(cdf_rawtime_to_datetime(start, cdf_type))}/"
                f"{format_datetime(cdf_rawtime_to_datetime(stop, cdf_type))}"
            )

        def _format_times_extent(times):
            return _format_time_range(times.min(), times.max())

        times, cdf_type = self._convert_time(times, cdf_type)

        if not variables: # stop here if no variables are requested
            return Dataset()

        if times.size == 0: # return an empty dataset
            return self._get_empty_dataset(variables)

        # get the time bounds
        start, stop = min(times), max(times)

        # load the source interpolated data
        dataset_iterator = self._subset(
            cdf_rawtime_to_datetime(start, cdf_type) - self.time_overlap,
            cdf_rawtime_to_datetime(stop, cdf_type) + self.time_overlap,
            variables,
        )

        self.logger.debug(
            "requested time-span: %s",
            LazyString(_format_time_range, start, stop)
        )

        dataset = Dataset()
        for item in dataset_iterator:
            if not item.is_empty:
                self.logger.debug(
                    "item time-span: %s",
                    LazyString(_format_times_extent, item[self.time_variable])
                )
            else:
                self.logger.debug("item time-span is empty")
            dataset.append(item)

        return dataset

    def _subset(self, start, stop, variables):
        """ Get subset of the time series overlapping the given time range.
        """
        def _format_time_range(start, stop):
            return f"{format_datetime(start)}/{format_datetime(stop)}"

        start = naive_to_utc(start)
        stop = naive_to_utc(stop)

        self.logger.debug("subset: %s", LazyString(_format_time_range, start, stop))
        self.logger.debug("extracted variables: %s", pretty_list(variables))

        if not variables: # stop here if no variables are requested
            return

        counter = 0
        for item in self.source.iter_products(start, stop, self.time_tolerance):
            product = item.data
            data_start = max(start, item.start)
            data_stop = min(stop, item.end)
            source_dataset = product.get_dataset(self.source.dataset_id)

            if not source_dataset:
                continue


            self.logger.debug("product: %s ", product.identifier)
            self.logger.debug(
                "subset time span: %s",
                LazyString(_format_time_range, data_start, data_stop)
            )

            time_subset = source_dataset.get('indexRange')
            if time_subset:
                time_subset = slice(*time_subset[:2])

            with CDFDataset(
                source_dataset['location'],
                translation=self.source.translate_fw,
                time_type=self.TIMESTAMP_TYPE,
            ) as cdf_ds:
                subset, nrv_shape = cdf_ds.get_temporal_subset(
                    time_variable=self.time_variable,
                    second_time_variable=self.second_time_variable,
                    max_record_duration=product.get_max_record_duration(
                        self.source.dataset_id
                    ),
                    start=data_start,
                    stop=data_stop,
                    subset=time_subset,
                    is_sorted=source_dataset.get('isSorted', True),
                )
                dataset = cdf_ds.extract_datset(
                    variables=variables,
                    subset=subset,
                    nrv_shape=nrv_shape,
                    ignored_variables=(self.COLLECTION_INDEX_VARIABLE,),
                )

            self.logger.debug("dataset length: %s ", dataset.length)

            if len(self.source.collections) > 1:
                self._add_collection_index(dataset, item.index)

            # do not record empty data selection
            if dataset.length:
                self.product_set.add(product.identifier) # record source product

            dataset.source = product.identifier # record source product

            yield dataset
            counter += 1

        # try to yield at least one empty dataset for a non-empty collection
        if counter < 1:
            dataset = self._get_empty_dataset(variables)
            if dataset:
                yield dataset

    def _add_collection_index(self, dataset, index):
        """ Add collection index to the given dataset. """
        dataset.set(
            self.COLLECTION_INDEX_VARIABLE,
            full(dataset.length, index, dtype="uint8"),
            CDF_UINT1_TYPE,
            self._collection_index_attrs,
        )

    @cached_property
    def _collection_index_attrs(self):
        """ Get collection index CDF attributes. """
        return {
            "DESCRIPTION": (
                "Index of the source data collection: {}".format(
                    ", ".join(
                        f"{index} - {collection.identifier}"
                        for index, collection
                        in enumerate(self.source.collections)
                    )
                )
            ),
            "UNITS": "-",
        }

    def _get_empty_dataset(self, variables):
        """ Get empty dataset. """
        # FIXME: generate empty response from the type definition
        self.logger.debug("empty dataset")
        self.logger.debug("extracted variables: %s", pretty_list(variables))

        # we need at least one product from the collection
        # to initialize correctly the empty variables
        product = self.source.get_sample_product()
        if product is None:
            self.logger.error(
                "Empty collection! The variables and their types cannot be "
                "reliably determined!"
            )
            raise RuntimeError(
                f"Empty product collection {self.source.identifier}!"
            )

        location = product.get_location(self.source.dataset_id)
        # generate an empty dataset from the sample product
        self.logger.debug("template product: %s", product.identifier)
        self.logger.debug("reading file: %s", location)
        with CDFDataset(
            location,
            translation=self.source.translate_fw,
            time_type=self.TIMESTAMP_TYPE,
        ) as cdf_ds:
            return cdf_ds.extract_datset(
                variables=variables,
                subset=slice(0, 0),
                nrv_shape=(0,),
                ignored_variables=(self.COLLECTION_INDEX_VARIABLE,),
            )
