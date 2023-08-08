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
# pylint: disable=too-few-public-methods,too-many-arguments

from logging import getLogger, LoggerAdapter
from datetime import timedelta
from vires.util import pretty_list, LazyString
from vires.cdf_util import cdf_rawtime_to_datetime
from vires.time_util import naive_to_utc, format_datetime
from vires.models import Product, ProductCollection
from vires.dataset import Dataset
from .base import TimeSeries
from .base_product import BaseProductTimeSeries
from .data_extraction import CDFDataset


class SwarmDefaultParameters():
    """ Default SWARM product parameters. """
    TIME_VARIABLE = "Timestamp"
    TIME_TOLERANCE = timedelta(microseconds=0) # time selection tolerance
    TIME_OVERLAP = timedelta(seconds=60) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(seconds=30) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=0.5)
    VARIABLE_INTERPOLATION_KINDS = {}


class MagLRParameters(SwarmDefaultParameters):
    """ MAGx_LR_1B parameters """
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


class GfzKpParameters(SwarmDefaultParameters):
    """ GFZ_KP parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(minutes=181) # time selection tolerance
    TIME_OVERLAP = timedelta(hours=6) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(minutes=181) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(minutes=180)
    VARIABLE_INTERPOLATION_KINDS = {
        'Kp': 'zero',
        'ap': 'zero',
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
    "GFZ_KP": GfzKpParameters,
}


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
        return f"{base_id}:{dataset_id}"


    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            collection_id = self.extra["collection_id"]
            return f"{collection_id}: {msg}", kwargs

    def __init__(self, collection, dataset_id=None, logger=None):

        if isinstance(collection, str):
            collection = self._get_collection(collection)

        dataset_id = collection.type.get_dataset_id(dataset_id)
        default_dataset_id = collection.type.default_dataset_id

        if dataset_id is None:
            raise ValueError("Missing mandatory dataset identifier!")

        if not collection.type.is_valid_dataset_id(dataset_id):
            raise ValueError(f"Invalid dataset identifier {dataset_id!r}!")

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

    @staticmethod
    def _get_collection(collection_name):
        try:
            return ProductCollection.objects.get(identifier=collection_name)
        except ProductCollection.DoesNotExist:
            raise RuntimeError(
                f"Non-existent product collection {collection_name}!"
            ) from None

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
            if not item.is_empty:
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
        start = naive_to_utc(start)
        stop = naive_to_utc(stop)

        self.logger.debug("subset: %s", LazyString(
            lambda: f"{format_datetime(start)}/{format_datetime(stop)}"
        ))
        self.logger.debug("extracted variables: %s", pretty_list(variables))

        if not variables: # stop here if no variables are requested
            return

        def _iter_products(query):
            """ Iterate over products returned by the query. Resolve temporal
            overlays of the products to prevent duplicate time coverage and
            yield applicable products and their time subset to be extracted.
            """
            products = iter(query.order_by('begin_time'))
            try:
                product = next(products)
            except StopIteration:
                return

            for next_product in products:
                end_time = min(product.end_time, next_product.begin_time)
                if end_time > product.begin_time:
                    yield product.begin_time, end_time, product
                product = next_product

            yield product.begin_time, product.end_time, product

        counter = 0
        for data_start, data_stop, product in _iter_products(self._subset_qs(start, stop)):
            data_start = max(start, data_start)
            data_stop = min(stop, data_stop)
            source_dataset = product.get_dataset(self.dataset_id)

            if not source_dataset:
                continue

            self.logger.debug("product: %s ", product.identifier)
            self.logger.debug("subset time span: %s", LazyString(
                lambda: (
                    f"{format_datetime(data_start)}/"
                    f"{format_datetime(data_stop)}"
                )
            ))

            self.product_set.add(product.identifier) # record source product

            time_subset = source_dataset.get('indexRange')
            if time_subset:
                time_subset = slice(*time_subset[:2])

            with CDFDataset(
                source_dataset['location'], translation=self.translate_fw,
                time_type=self.TIMESTAMP_TYPE,
            ) as cdf_ds:
                subset, nrv_shape = cdf_ds.get_temporal_subset(
                    time_variable=self.time_variable,
                    start=data_start,
                    stop=data_stop,
                    subset=time_subset,
                    is_sorted=source_dataset.get('isSorted', True),
                )
                dataset = cdf_ds.extract_datset(
                    variables=variables,
                    subset=subset,
                    nrv_shape=nrv_shape
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

    def _subset_qs(self, start, stop):
        """ Subset Django query set. """
        _start = start - self.time_tolerance
        _stop = stop + self.time_tolerance
        return Product.objects.prefetch_related('collection__type').filter(
            collection=self.collection,
            begin_time__lt=_stop,
            end_time__gte=_start,
            begin_time__gte=(_start - self.collection.max_product_duration),
        )

    def _get_empty_dataset(self, variables):
        """ Get empty dataset. """
        # FIXME: generate empty response from the type definition
        self.logger.debug("empty dataset")
        self.logger.debug("extracted variables: %s", pretty_list(variables))

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
                f"Empty product collection {self.collection.identifier}!"
            ) from None
        else:
            location = product.get_location(self.collection.type.default_dataset_id)
            # generate an empty dataset from the sample product
            self.logger.debug("template product: %s", product.identifier)
            self.logger.debug("reading file: %s", location)
            with CDFDataset(
                location, translation=self.translate_fw,
                time_type=self.TIMESTAMP_TYPE,
            ) as cdf_ds:
                return cdf_ds.extract_datset(
                    variables=variables,
                    subset=slice(0, 0),
                    nrv_shape=(0,),
                )
