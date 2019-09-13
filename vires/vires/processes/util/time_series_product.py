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
# pylint: disable=too-many-locals, too-many-arguments, too-few-public-methods
# pylint: disable=too-many-instance-attributes

from logging import getLogger, LoggerAdapter
from datetime import timedelta
from numpy import searchsorted, broadcast_to
from eoxserver.backends.access import connect
from vires.cdf_util import (
    cdf_open, datetime_to_cdf_rawtime, cdf_rawtime_to_datetime,
    timedelta_to_cdf_rawtime, CDF_EPOCH_TYPE,
)
from vires.models import Product, ProductCollection
from vires.dataset import Dataset
from .time_series import TimeSeries


class SwarmDefaultParameters(object):
    """ Default SWARM product parameters. """
    TIME_VARIABLE = "Timestamp"
    TIME_TOLERANCE = timedelta(microseconds=10) # time selection tolerance
    TIME_OVERLAP = timedelta(seconds=60) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(seconds=30) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=0.5)
    VARIABLE_TRANSLATES = {}
    VARIABLE_INTERPOLATION_KINDS = {}


class SwarmEEFParameters(SwarmDefaultParameters):
    """ Default SWARM product parameters. """
    VARIABLE_TRANSLATES = {
        'Timestamp': 'timestamp',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    }


class AuxImf2Parameters(SwarmDefaultParameters):
    """ AUX_IMF_2_ parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(minutes=61) # time selection tolerance
    TIME_OVERLAP = timedelta(hours=2) # time interpolation overlap
    TIME_GAP_THRESHOLD = timedelta(minutes=61) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(minutes=60)
    VARIABLE_TRANSLATES = {
        'Timestamp': 'Epoch',
        'IMF_BY_GSM': 'BY_GSM',
        'IMF_BZ_GSM': 'BZ_GSM',
        'IMF_V': 'V',
    }
    VARIABLE_INTERPOLATION_KINDS = {
        'F10_INDEX': 'zero',
        'IMF_BY_GSM': 'zero',
        'IMF_BZ_GSM': 'zero',
        'IMF_V': 'zero',
    }


class SwarmAEJParameters(SwarmDefaultParameters):
    """ AEJ product parameters. """
    VARIABLE_TRANSLATES = {
        'Timestamp': 't',
        'MLT_QD': 'MLT',
    }


class SwarmAEJLPSParameters(SwarmDefaultParameters):
    """ AEJxLPS product parameters. """
    VARIABLE_TRANSLATES = {
        'Timestamp': 't',
        'Latitude': 'lat_GD',
        'Longitude': 'long_GD',
        'Latitude_QD': 'lat_QD',
        'Longitude_QD': 'long_QD',
        'MLT_QD': 'mlt_QD',
        'J_CF': 'JCF_GEO',
        'J_DF': 'JDF_GEO',
        'J_CF_SemiQD': 'JCF_SemiQD',
        'J_DF_SemiQD': 'JDF_SemiQD',
        'J_C': 'JC',
    }


DEFAULT_PRODUCT_TYPE_PARAMETERS = SwarmDefaultParameters #pylint: disable=invalid-name
PRODUCT_TYPE_PARAMETERS = {
    "SWARM_EEF": SwarmEEFParameters,
    "AUX_IMF_2_": AuxImf2Parameters,
    "SWARM_AEJ_LPL": SwarmAEJParameters,
    "SWARM_AEJ_LPS": SwarmAEJLPSParameters,
    "SWARM_AEJ_BPL": SwarmAEJParameters,
    "SWARM_AEJ_PBL": SwarmAEJParameters,
    "SWARM_AOB_FAC": SwarmAEJParameters,
}


class BaseProductTimeSeries(TimeSeries):
    """ Base product time-series """

    def __init__(self, logger=None, **kwargs):
        super(BaseProductTimeSeries, self).__init__()
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

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["collection_id"], msg), kwargs

    def __init__(self, collection, logger=None):
        if isinstance(collection, basestring):
            collection = self._get_collection(collection)

        params = PRODUCT_TYPE_PARAMETERS.get(
            collection.range_type.name, DEFAULT_PRODUCT_TYPE_PARAMETERS
        )

        super(ProductTimeSeries, self).__init__(
            logger=self._LoggerAdapter(logger or getLogger(__name__), {
                "collection_id": collection.identifier,
            }),
            time_variable=params.TIME_VARIABLE,
            time_tolerance=params.TIME_TOLERANCE,
            time_overlap=params.TIME_OVERLAP,
            time_gap_threshold=params.TIME_GAP_THRESHOLD,
            segment_neighbourhood=params.TIME_SEGMENT_NEIGHBOURHOOD,
            interpolation_kinds=params.VARIABLE_INTERPOLATION_KINDS,
        )

        self.collection = collection
        self.translate_fw = dict(params.VARIABLE_TRANSLATES)
        self.translate_bw = dict((v, k) for k, v in self.translate_fw.iteritems())

    @property
    def collection_identifier(self):
        """ Get collection identifier. """
        return self.collection.identifier

    @property
    def variables(self):
        return [
            self.translate_bw.get(band.identifier, band.identifier)
            for band in self.collection.range_type
        ]

    def _extract_dataset(self, cdf, extracted_variables, idx_low, idx_high):
        """ Extract dataset from a product. """
        dataset = Dataset()
        for variable in extracted_variables:
            cdf_var = cdf.raw_var(self.translate_fw.get(variable, variable))
            if cdf_var.rv(): # regular record variable
                data = cdf_var[idx_low:idx_high]
            else: # NRV variable
                value = cdf_var[...]
                size = max(0, idx_high - idx_low)
                data = broadcast_to(value, (size,) + value.shape[1:])
            dataset.set(variable, data, cdf_var.type(), cdf_var.attrs)
        return dataset

    def _get_empty_dataset(self, variables):
        """ Get empty dataset. """
        self.logger.debug("empty dataset")
        self.logger.debug("extracted variables %s", variables)

        try:
            # we need at least one product from the collection
            # to initialize correctly the empty variables
            product = Product.objects.filter(
                collections=self.collection
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
            # generate an empty dataset from the sample product
            self.logger.debug("template product: %s ", product.identifier)
            with cdf_open(connect(product.data_items.all()[0])) as cdf:
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
            self.logger.debug("product: %s ", product.identifier)

            self.product_set.add(product.identifier) # record source product

            with cdf_open(connect(product.data_items.all()[0])) as cdf:
                # temporal sub-setting
                temp_var = cdf.raw_var(
                    self.translate_fw.get(self.time_variable, self.time_variable)
                )
                times, time_type = temp_var[:], temp_var.type()

                self.logger.debug(
                    "product time span %s %s",
                    cdf_rawtime_to_datetime(times[0], time_type),
                    cdf_rawtime_to_datetime(times[-1], time_type),
                )

                low, high = searchsorted(times, [
                    datetime_to_cdf_rawtime(start, time_type),
                    datetime_to_cdf_rawtime(stop, time_type),
                ], 'left')

                self.logger.debug("product slice %s:%s", low, high)

                dataset = self._extract_dataset(cdf, variables, low, high)

            self.logger.debug("dataset length: %s ", dataset.length)

            yield dataset
            counter += 1

        # try to yield at least one empty dataset for a non-empty collection
        if counter < 1:
            dataset = self._get_empty_dataset(variables)
            if dataset:
                yield dataset

    def _subset_qs(self, start, stop):
        """ Subset Django query set. """
        return Product.objects.filter(
            collections=self.collection,
            begin_time__lt=(stop + self.time_tolerance),
            end_time__gte=(start - self.time_tolerance),
        )

    @staticmethod
    def _get_collection(collection_name):
        try:
            return ProductCollection.objects.get(identifier=collection_name)
        except ProductCollection.DoesNotExist:
            raise RuntimeError(
                "Non-existent product collection %s!" % collection_name
            )
