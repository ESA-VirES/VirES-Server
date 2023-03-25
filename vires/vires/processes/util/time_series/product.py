#-------------------------------------------------------------------------------
#
# Data Source - product time-series class
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
# pylint: disable=too-many-locals, too-many-arguments, too-few-public-methods
# pylint: disable=too-many-instance-attributes

from logging import getLogger, LoggerAdapter
from datetime import timedelta
from numpy import searchsorted, broadcast_to, asarray
from vires.cdf_util import (
    cdf_open, datetime_to_cdf_rawtime, cdf_rawtime_to_datetime,
    timedelta_to_cdf_rawtime, cdf_type_map, CDF_EPOCH_TYPE,
)
from vires.time_util import naive_to_utc
from vires.models import Product, ProductCollection
from vires.dataset import Dataset
from .base import TimeSeries


class SwarmDefaultParameters():
    """ Default SWARM product parameters. """
    TIME_VARIABLE = "Timestamp"
    TIME_TOLERANCE = timedelta(microseconds=0) # time selection tolerance
    TIME_OVERLAP = timedelta(seconds=60) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(seconds=30) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=0.5)
    VARIABLE_INTERPOLATION_KINDS = {}


class MagLRParameters(SwarmDefaultParameters):
    VARIABLE_INTERPOLATION_KINDS = {
        "B_NEC": "linear",
        "F": "linear",
    }


class AuxImf2Parameters(SwarmDefaultParameters):
    """ AUX_IMF_2_ parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(minutes=61) # time selection tolerance
    TIME_OVERLAP = timedelta(hours=2) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(minutes=61) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(minutes=60)
    VARIABLE_INTERPOLATION_KINDS = {
        'F10_INDEX': 'zero',
        'IMF_BY_GSM': 'zero',
        'IMF_BZ_GSM': 'zero',
        'IMF_V': 'zero',
    }


class OmniHr1MinParameters(SwarmDefaultParameters):
    """ OMNI HR 1min parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(0) # time selection tolerance
    TIME_OVERLAP = timedelta(minutes=120) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(seconds=61) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=60)
    VARIABLE_INTERPOLATION_KINDS = {
        'IMF_BY_GSM': 'linear',
        'IMF_BZ_GSM': 'linear',
        'IMF_V': 'linear',
        'IMF_Vx': 'linear',
        'IMF_Vy': 'linear',
        'IMF_Vz': 'linear',
    }


DEFAULT_PRODUCT_TYPE_PARAMETERS = SwarmDefaultParameters #pylint: disable=invalid-name
PRODUCT_TYPE_PARAMETERS = {
    "SW_MAGx_LR_1B": MagLRParameters,
    "SW_AUX_IMF_2_": AuxImf2Parameters,
    "OMNI_HR_1min": OmniHr1MinParameters,
}


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

    def _subset_times(self, times, variables, cdf_type=CDF_EPOCH_TYPE):
        """ Get subset of the time series overlapping the give array time array.
        """
        raise NotImplementedError

    def subset_count(self, start, stop):
        """ Count matched number of products. """
        return self._subset_qs(start, stop).count()

    def subset(self, start, stop, variables=None):
        variables = self.get_extracted_variables(variables)
        return iter(self._subset(start, stop, variables))

    def subset_times(self, times, variables=None, cdf_type=CDF_EPOCH_TYPE):
        """ Get subset of the time series overlapping the given time array.
        """
        variables = self.get_extracted_variables(variables)
        self.logger.debug("requested variables %s", variables)
        return self._subset_times(times, variables, cdf_type)

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=CDF_EPOCH_TYPE, valid_only=False):

        variables = self.get_extracted_variables(variables)
        self.logger.debug("requested variables %s", variables)

        if not variables:
            return Dataset()

        if self.time_variable not in variables:
            subset_variables = [self.time_variable] + variables
        else:
            subset_variables = variables

        dataset = self._subset_times(times, subset_variables, cdf_type)

        self.logger.debug("requested dataset length %s", len(times))

        if dataset and dataset.length > 0:
            _times = dataset[self.time_variable]
            self.logger.debug(
                "interpolated time-span %s, %s",
                cdf_rawtime_to_datetime(_times.min(), cdf_type),
                cdf_rawtime_to_datetime(_times.max(), cdf_type),
            )
        else:
            self.logger.debug("interpolated time-span is empty")

        self.logger.debug("interpolated dataset length: %s ", dataset.length)

        if not dataset:
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


class ProductTimeSeries(BaseProductTimeSeries):
    """ Product time-series class. """

    @staticmethod
    def _get_variable_mapping(dataset_definition):
        return {
            variable: source
            for variable, source in (
                (variable, type_info.get('source'))
                for variable, type_info in dataset_definition.items()
            ) if source
        }

    @staticmethod
    def _get_id(base_id, dataset_id, default_dataset_id):
        if dataset_id == default_dataset_id:
            return base_id
        return "%s:%s" % (base_id, dataset_id)


    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["collection_id"], msg), kwargs

    def __init__(self, collection, dataset_id=None, logger=None):

        if isinstance(collection, str):
            collection = self._get_collection(collection)

        dataset_id = collection.type.get_dataset_id(dataset_id)
        default_dataset_id = collection.type.default_dataset_id

        if dataset_id is None:
            raise ValueError("Missing mandatory dataset identifier!")

        if not collection.type.is_valid_dataset_id(dataset_id):
            raise ValueError("Invalid dataset identifier %r!" % dataset_id)

        params = PRODUCT_TYPE_PARAMETERS.get(
            self._get_id(
                collection.type.identifier,
                collection.type.get_base_dataset_id(dataset_id),
                default_dataset_id,
            ),
            DEFAULT_PRODUCT_TYPE_PARAMETERS,
        )

        super().__init__(
            logger=self._LoggerAdapter(logger or getLogger(__name__), {
                "collection_id": self._get_id(
                    collection.identifier, dataset_id, default_dataset_id
                ),
            }),
            time_variable=params.TIME_VARIABLE,
            time_tolerance=params.TIME_TOLERANCE,
            time_overlap=params.TIME_OVERLAP,
            time_gap_threshold=params.TIME_GAP_THRESHOLD,
            segment_neighbourhood=params.TIME_SEGMENT_NEIGHBOURHOOD,
            interpolation_kinds=params.VARIABLE_INTERPOLATION_KINDS,
        )

        self.collection = collection
        self.dataset_id = dataset_id
        self.default_dataset_id = default_dataset_id

        self.translate_fw = self._get_variable_mapping(
            self.collection.type.get_dataset_definition(self.dataset_id)
        )

    @property
    def metadata(self):
        """ Get collection metadata. """
        metadata = self.collection.metadata
        metadata.update(self.collection.spacecraft_dict)
        return metadata

    @property
    def collection_identifier(self):
        """ Get collection identifier. """
        return self._get_id(
            self.collection.identifier, self.dataset_id, self.default_dataset_id
        )

    @property
    def variables(self):
        return list(
            self.collection.type.get_dataset_definition(self.dataset_id)
        )

    def _extract_dataset(self, cdf, extracted_variables, idx_low, idx_high):
        """ Extract dataset from a product. """
        dataset = Dataset()
        for variable in extracted_variables:
            cdf_var = cdf.raw_var(self.translate_fw.get(variable, variable))
            if cdf_var.rv(): # regular record variable
                data = cdf_var[idx_low:idx_high]
            else: # NRV variable
                value = asarray(cdf_var[...])
                size = max(0, idx_high - idx_low)
                data = broadcast_to(value, (size,) + value.shape)
            dataset.set(
                variable, data, cdf_type_map(cdf_var.type()), cdf_var.attrs
            )
        return dataset

    def _get_empty_dataset(self, variables):
        """ Get empty dataset. """
        # FIXE: generate empty response from the type definition
        self.logger.debug("empty dataset")
        self.logger.debug("extracted variables %s", variables)

        try:
            # we need at least one product from the collection
            # to initialize correctly the empty variables
            product = Product.objects.filter(
                collection=self.collection
            ).order_by('begin_time')[0]
        except IndexError:
            self.logger.error(
                "Empty collection! The variables and their types cannot be "
                "reliably determined!"
            )
            raise RuntimeError(
                "Empty product collection %s!" % self.collection.identifier
            )
        else:
            location = product.get_location(self.collection.type.default_dataset_id)
            # generate an empty dataset from the sample product
            self.logger.debug("template product: %s", product.identifier)
            self.logger.debug("reading file: %s", location)
            with cdf_open(location) as cdf:
                return self._extract_dataset(cdf, variables, 0, 0)


    def _subset_times(self, times, variables, cdf_type=CDF_EPOCH_TYPE):
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

        self.logger.debug(
            "requested time-span [%s, %s]",
            cdf_rawtime_to_datetime(start, cdf_type),
            cdf_rawtime_to_datetime(stop, cdf_type)
        )

        dataset = Dataset()
        for item in dataset_iterator:
            if item and item.length > 0:
                _times = item[self.time_variable]
                self.logger.debug(
                    "item time-span [%s, %s]",
                    cdf_rawtime_to_datetime(_times.min(), cdf_type),
                    cdf_rawtime_to_datetime(_times.max(), cdf_type),
                )
            else:
                self.logger.debug("item time-span is empty")
            dataset.append(item)

        return dataset

    def _subset(self, start, stop, variables):
        """ Get subset of the time series overlapping the given time range.
        """
        self.logger.debug("subset: %s %s", start, stop)
        self.logger.debug("extracted variables %s", variables)

        if not variables: # stop here if no variables are requested
            return

        counter = 0
        for product in self._subset_qs(start, stop).order_by('begin_time'):
            source_dataset = product.get_dataset(self.dataset_id)

            if not source_dataset:
                continue

            self.logger.debug("product: %s ", product.identifier)
            self.logger.debug(
                "product time span: %s/%s", product.begin_time, product.end_time
            )

            self.product_set.add(product.identifier) # record source product

            start_index, stop_index = source_dataset.get('indexRange') or [0, None]

            if source_dataset.get('isSorted', True):
                extract_time_subset = self._extract_time_subset_sorted
            else:
                extract_time_subset = self._extract_time_subset_unsorted

            with cdf_open(source_dataset['location']) as cdf:
                # temporal sub-setting
                temp_var = cdf.raw_var(
                    self.translate_fw.get(self.time_variable, self.time_variable)
                )
                times, time_type = temp_var[:], temp_var.type()

                dataset = extract_time_subset(
                    cdf, variables, times, start_index, stop_index,
                    datetime_to_cdf_rawtime(start, time_type),
                    datetime_to_cdf_rawtime(stop, time_type),
                )

            self.logger.debug("dataset length: %s ", dataset.length)

            dataset.source = product.identifier # record source product

            yield dataset
            counter += 1

        # try to yield at least one empty dataset for a non-empty collection
        if counter < 1:
            dataset = self._get_empty_dataset(variables)
            if dataset:
                yield dataset

    def _extract_time_subset_sorted(self, cdf, variables, times,
                                    start_index, stop_index,
                                    start_time, stop_time):
        start, stop = searchsorted(
            times[start_index:stop_index], [start_time, stop_time], 'left'
        )
        start += start_index
        stop += start_index
        self.logger.debug("product slice %s:%s", start, stop)
        return self._extract_dataset(cdf, variables, start, stop)

    def _extract_time_subset_unsorted(self, cdf, variables, times,
                                      start_index, stop_index,
                                      start_time, stop_time):
        index = times[start_index:stop_index].argsort(kind='stable')
        if start_index > 0:
            index += start_index
        start, stop = searchsorted(times[index], [start_time, stop_time], 'left')
        index = index[start:stop]
        if index.size > 0:
            start, stop = index.min(), index.max() + 1
        else:
            start, stop = 0, 0
        self.logger.debug("product slice %s:%s", start, stop)
        dataset = self._extract_dataset(cdf, variables, start, stop)
        if start > 0:
            index -= start
        return dataset.subset(index)

    def _extract_dataset_by_index(self, cdf, extracted_variables, index):
        index = asarray(index)
        if index.size > 0:
            start, stop = index.min(), index.max()
        else:
            start, stop = 0, 0
        dataset = self._extract_dataset(cdf, extracted_variables, start, stop)
        return dataset.subset(index - start)


    def _subset_qs(self, start, stop):
        """ Subset Django query set. """
        _start = naive_to_utc(start) - self.time_tolerance
        _stop = naive_to_utc(stop) + self.time_tolerance
        return Product.objects.prefetch_related('collection__type').filter(
            collection=self.collection,
            begin_time__lt=_stop,
            end_time__gte=_start,
            begin_time__gte=(_start - self.collection.max_product_duration),
        )

    @staticmethod
    def _get_collection(collection_name):
        try:
            return ProductCollection.objects.get(identifier=collection_name)
        except ProductCollection.DoesNotExist:
            raise RuntimeError(
                "Non-existent product collection %s!" % collection_name
            )
