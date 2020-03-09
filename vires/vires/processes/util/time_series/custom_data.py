#-------------------------------------------------------------------------------
#
# Data Source - custom dataset time-series class
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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

import json
from ctypes import c_long
from logging import getLogger, LoggerAdapter
from numpy import empty, argsort, searchsorted, broadcast_to, asarray
from vires.cdf_util import (
    cdf_open, cdf_rawtime_to_datetime, datetime_to_cdf_rawtime,
    CDF_EPOCH_TYPE,
)
from vires.models import CustomDataset
from vires.dataset import Dataset
from vires.util import cached_property
from vires.views.custom_data import sanitize_info
from .product import BaseProductTimeSeries, DEFAULT_PRODUCT_TYPE_PARAMETERS


class CustomDatasetTimeSeries(BaseProductTimeSeries):
    """ Custom dataset time-series class. """
    # fake collection metadata
    metadata = {
        "spacecraft": "U",
    }
    COLLECTION_IDENTIFIER = "USER_DATA"
    TIME_VARIABLE = "Timestamp"

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'CustomDataset[%s]: %s' % (self.extra["username"], msg), kwargs

    def __init__(self, user, logger=None):
        params = DEFAULT_PRODUCT_TYPE_PARAMETERS

        super().__init__(
            logger=self._LoggerAdapter(logger or getLogger(__name__), {
                "username": user.username if user else "<anonymous-user>"
            }),
            time_variable=params.TIME_VARIABLE,
            time_tolerance=params.TIME_TOLERANCE,
            time_overlap=params.TIME_OVERLAP,
            time_gap_threshold=params.TIME_GAP_THRESHOLD,
            segment_neighbourhood=params.TIME_SEGMENT_NEIGHBOURHOOD,
            interpolation_kinds=params.VARIABLE_INTERPOLATION_KINDS,
        )

        self.user = user

    @property
    def collection_identifier(self):
        """ Get collection identifier. """
        return self.COLLECTION_IDENTIFIER

    @property
    def variables(self):
        return list(self._variables)

    def _subset_times(self, times, variables, cdf_type=CDF_EPOCH_TYPE):
        """ Get subset of the time series overlapping the give array time array.
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
        self.logger.debug("subset: %s %s", start, stop)
        self.logger.debug("extracted variables %s", variables)

        if not variables: # stop here if no variables are requested
            return

        for dataset in self._subset_qs(start, stop):
            self.logger.debug(
                "custom dataset: %s/%s", dataset.identifier, dataset.filename
            )

            self.product_set.add(dataset.filename) # record source filename

            with cdf_open(dataset.location) as cdf:
                # temporal sub-setting
                temp_var = cdf.raw_var(self.TIME_VARIABLE)
                times, time_type = temp_var[:], temp_var.type()

                # note: data are not ordered!
                idx = argsort(times)

                self.logger.debug(
                    "dataset time span %s %s",
                    cdf_rawtime_to_datetime(times[idx[0]], time_type),
                    cdf_rawtime_to_datetime(times[idx[-1]], time_type),
                )

                low, high = searchsorted(times[idx], [
                    datetime_to_cdf_rawtime(start, time_type),
                    datetime_to_cdf_rawtime(stop, time_type),
                ], 'left')

                idx = idx[low:high]

                self.logger.debug("product slice %s:%s", low, high)

                dataset = self._extract_dataset(cdf, variables, idx)

            self.logger.debug("dataset length: %s ", dataset.length)

            yield dataset

    def _get_empty_dataset(self, variables):
        """ Get empty dataset. """
        self.logger.debug("empty dataset")
        self.logger.debug("extracted variables %s", variables)

        variable_types = self._variables

        dataset = Dataset()
        for variable in variables:
            type_ = variable_types.get(variable)
            if not type_:
                continue

            dataset.set(
                variable, empty((0,) + type_['shape']),
                c_long(type_['cdf_type']), type_.get('attributes', {})
            )

        return dataset

    @staticmethod
    def _extract_dataset(cdf, extracted_variables, idx):
        """ Extract dataset from a product. """
        if idx.size == 0:
            idx_low, idx_high = 0, 0
        else:
            idx_low, idx_high = idx.min(), idx.max() + 1
            if idx_low != 0:
                idx = idx - idx_low

        dataset = Dataset()
        for variable in extracted_variables:
            cdf_var = cdf.raw_var(variable)
            if cdf_var.rv(): # regular record variable
                data = cdf_var[idx_low:idx_high][idx]
            else: # NRV variable
                value = asarray(cdf_var[...])
                data = broadcast_to(value, (idx.size,) + value.shape[1:])
            dataset.set(variable, data, cdf_var.type(), cdf_var.attrs)
        return dataset

    def _subset_qs(self, start, stop):
        """ Temporal subset Django query set. """
        # multiple uploads
        #return CustomDataset.objects.filter(
        #    owner=self.user, is_valid=True, start__lt=stop, end__gte=start,
        #).order_by('start')
        # single upload
        return [
            dataset for dataset in self._all_qs()
            if dataset.start < stop and dataset.end >= start
        ]

    def _all_qs(self):
        """ all items Django query set. """
        # multiple uploads
        #return CustomDataset.objects.filter(owner=self.user, is_valid=True)
        # single upload
        return (
            CustomDataset.objects
            .filter(owner=self.user, is_valid=True)
            .order_by('-created')[:1]
        )

    @cached_property
    def _variables(self):

        def _load_variables(dataset):
            return sanitize_info(json.loads(dataset.info))['fields']

        def _not_equal(type1, type2):
            return (
                type1['cdf_type'] != type2['cdf_type'] or
                type1['shape'] != type2['shape']
            )

        #Note only variables common to all datasets are published.
        variables = None
        for dataset in self._all_qs():
            dataset_variables = _load_variables(dataset)
            if variables is None:
                variables = dataset_variables
            else:
                for variable, type_ in dataset_variables.items():
                    type__ref = variables.get(variable)
                    if type__ref and _not_equal(type__ref, type_):
                        del variables[variable]
        return variables or {}
