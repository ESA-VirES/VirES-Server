#-------------------------------------------------------------------------------
#
# Data Source - cached model - data extraction
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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

from os.path import exists
from logging import getLogger, LoggerAdapter
from collections import defaultdict
from numpy import empty, full, nan
from vires.cdf_util import cdf_rawtime_to_datetime
from vires.time_util import naive_to_utc, format_datetime
from vires.util import include, exclude, pretty_list, LazyString
from vires.models import Product
from vires.dataset import Dataset
from vires.management.api.cached_magnetic_model import (
    get_collection_model_cache_directory,
    get_product_model_cache_file,
    read_sources_with_time_ranges,
    extract_model_sources_datetime,
)
from .base import TimeSeries
from .base_product import BaseProductTimeSeries
from .product import DEFAULT_PRODUCT_TYPE_PARAMETERS
from .data_extraction import CDFDataset


class CachedModelExtraction(BaseProductTimeSeries):
    """ Cached model time-series class. """

    @staticmethod
    def _get_variable_mapping(dataset_definition):
        return {
            variable: source
            for variable, source in (
                (variable, type_info.get('source'))
                for variable, type_info in dataset_definition.items()
            ) if source
        }

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            collection_id = self.extra["collection_id"]
            return f"{collection_id}: cached model: {msg}", kwargs

    @property
    def variables(self):
        return list(self.models)

    def __init__(self, collection, source_models, logger=None, master_collection=None):
        self.collection = collection
        self.models = {
            f"__cached__B_NEC_{model.name}": model
            for model in source_models
        }
        self.dataset_id = collection.type.default_dataset_id
        self.translate_fw = self._get_variable_mapping(
            self.collection.type.get_dataset_definition(self.dataset_id)
        )
        self.translate_fw_models = {
            f"__cached__B_NEC_{model.name}": f"B_NEC_{model.name}"
            for model in source_models
        }

        if master_collection == self.collection:
            # Force nearest neighbour interpolation when the cached collection
            # is the master collection, i.e., the cached locations are
            # the same as the interpolated ones.
            inderpolation_kind = "nearest"
        else:
            inderpolation_kind = (
                (collection.metadata.get("cachedMagneticModels") or {})
                .get("interpolationKind", "nearest")
            )
        params = DEFAULT_PRODUCT_TYPE_PARAMETERS

        super().__init__(
            logger=self._LoggerAdapter(logger or getLogger(__name__), {
                "collection_id": collection.identifier
            }),
            time_variable=params.TIME_VARIABLE,
            time_tolerance=params.TIME_TOLERANCE,
            time_overlap=params.TIME_OVERLAP,
            time_gap_threshold=params.TIME_GAP_THRESHOLD,
            segment_neighbourhood=params.TIME_SEGMENT_NEIGHBOURHOOD,
            interpolation_kinds={
                variable: inderpolation_kind for variable in self.models
            },
        )

        if master_collection == self.collection:
            self.logger.debug("using master collection")
        self.logger.debug("interpolation kind: %s", inderpolation_kind)

    def _subset_times(self, times, variables, cdf_type=TimeSeries.TIMESTAMP_TYPE):
        """ Get subset of the time series overlapping the given time array.
        """
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

        self.logger.debug("requested time-span: %s", LazyString(lambda: (
            f"{format_datetime(cdf_rawtime_to_datetime(start, cdf_type))}/"
            f"{format_datetime(cdf_rawtime_to_datetime(stop, cdf_type))}"
        )))

        dataset = Dataset()
        for item in dataset_iterator:
            if item and item.length > 0:
                _times = item[self.time_variable]
                self.logger.debug("item time-span: %s", LazyString(lambda: (
                    f"{format_datetime(cdf_rawtime_to_datetime(_times.min(), cdf_type))}/"
                    f"{format_datetime(cdf_rawtime_to_datetime(_times.max(), cdf_type))}"
                )))
            else:
                self.logger.debug("item time-span is empty")
            dataset.append(item)

        return dataset

    def _subset(self, start, stop, variables):
        """ Get subset of the time series overlapping the given time range.
        """
        self.logger.debug("subset: %s", LazyString(
            lambda: f"{format_datetime(start)}/{format_datetime(stop)}"
        ))
        self.logger.debug("extracted variables: %s", pretty_list(variables))

        if not variables: # stop here if no variables are requested
            return

        cache_directory = get_collection_model_cache_directory(
            self.collection.identifier
        )

        counter = 0
        for product in self._subset_qs(start, stop).order_by('begin_time'):
            source_dataset = product.get_dataset(self.dataset_id)

            if not source_dataset:
                continue

            self.logger.debug("product: %s ", product.identifier)
            self.logger.debug("product time span: %s", LazyString(
                lambda: (
                    f"{format_datetime(product.begin_time,)}/"
                    f"{format_datetime(product.end_time)}"
                )
            ))

            self.product_set.add(product.identifier) # record source product

            time_subset = source_dataset.get('indexRange')
            if time_subset:
                time_subset = slice(*subset[:2])

            with CDFDataset(
                source_dataset['location'], translation=self.translate_fw,
                time_type=self.TIMESTAMP_TYPE,
            ) as cdf_ds:
                subset, nrv_shape = cdf_ds.get_temporal_subset(
                    self.time_variable,
                    start=start,
                    stop=stop,
                    subset=time_subset,
                    is_sorted=source_dataset.get('isSorted', True),
                )
                dataset = cdf_ds.extract_datset(
                    variables=list(exclude(variables, self.models)),
                    subset=subset,
                    nrv_shape=nrv_shape
                )

            self.logger.debug("dataset length: %s", dataset.length)

            model_variables = set(include(variables, self.models))
            available_model_variables = set()
            extracted_model_variables = set()
            cache_file = get_product_model_cache_file(
                cache_directory, product.identifier
            )

            if exists(cache_file):
                with CDFDataset(
                    cache_file, translation=self.translate_fw_models,
                    time_type=self.TIMESTAMP_TYPE,
                ) as cdf_ds:

                    # get available model variables
                    available_model_variables = set(
                        variable for variable in model_variables
                        if self.translate_fw_models[variable] in cdf_ds.cdf
                    )

                    # get expected model source
                    expected_sources = self._extract_model_sources(
                        start, stop,
                        variables=available_model_variables,
                    )

                    # get sources of the cached models
                    cached_sources = self._extract_cached_model_sources(
                        start, stop,
                        variables=available_model_variables,
                        sources=read_sources_with_time_ranges(cdf_ds.cdf),
                    )

                    # filter out outdated cached models
                    extracted_model_variables = set(
                        variable for variable in available_model_variables
                        if expected_sources[variable] == cached_sources[variable]
                    )

                    dataset.merge(cdf_ds.extract_datset(
                        variables=extracted_model_variables,
                        subset=subset,
                        nrv_shape=nrv_shape
                    ))

                    self._update_sources(cached_sources, extracted_model_variables)

            self.logger.debug(
                "extracted model variables: %s",
                pretty_list(extracted_model_variables)
            )

            obsolete_variables = available_model_variables - extracted_model_variables
            if obsolete_variables:
                self.logger.warning(
                    "obsolete cached models detected: %s",
                    pretty_list(
                        self.models[variable].name
                        for variable in obsolete_variables
                    )
                )

            missing_model_variables = (
                model_variables.difference(extracted_model_variables)
            )

            self.logger.debug(
                "missing model variables: %s",
                pretty_list(missing_model_variables)
            )

            self._fill_missing_model_variables(dataset, missing_model_variables)

            yield dataset
            counter += 1

        # try to yield at least one empty dataset for a non-empty collection
        if counter < 1:
            dataset = self._get_empty_dataset(variables)
            if dataset:
                yield dataset

    def _get_empty_dataset(self, variables):
        """ Generate an empty dataset. """
        dataset = Dataset()
        times = self._convert_time(empty((0,), dtype="float64"), None)
        dataset.set(self.time_variable, times, self.TIMESTAMP_TYPE, {})
        self._fill_missing_model_variables(
            dataset, set(include(variables, self.models))
        )
        return dataset

    def _fill_missing_model_variables(self, dataset, variables):
        """ Fill missing model variables with NaN values.
        """
        if not variables:
            return
        fill_data = full((*dataset[self.time_variable].shape, 3), nan, dtype="float64")
        for variable in variables:
            _, cdf_type, attrs = (
                self.models[variable]
                ._output[self.translate_fw_models[variable]]
            )
            dataset.set(variable, fill_data, cdf_type, attrs)

    def _extract_model_sources(self, start, end, variables):
        """ Extract sources from the applicable models. """
        return {
            variable: set(extract_model_sources_datetime(
                self.models[variable].source_model, start, end
            ))
            for variable in variables
        }

    def _extract_cached_model_sources(self, start, end, variables, sources):
        """ Extract sources of the cached model values. """
        model_to_variable = {
            self.models[variable].name: variable
            for variable in variables
        }
        model_sources = defaultdict(set)
        for model_name, source, validity_start, validity_end in sources:
            variable = model_to_variable.get(model_name)
            if (
                variable is not None and
                validity_start <= end and
                validity_end >= start
            ):
                model_sources[variable].add(source)
        return model_sources

    def _update_sources(self, sources, variables):
        """ Update product sources from the extracted cached model sources.
        """
        for variable in variables:
            for source in sources[variable]:
                self.product_set.add(source)

    def _subset_qs(self, start, stop):
        """ Subset Django query set. """
        _start = naive_to_utc(start)
        _stop = naive_to_utc(stop)
        return Product.objects.prefetch_related('collection__type').filter(
            collection=self.collection,
            begin_time__lt=_stop,
            end_time__gte=_start,
            begin_time__gte=(_start - self.collection.max_product_duration),
        )
