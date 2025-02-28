#-------------------------------------------------------------------------------
#
# Data Source - convenience wrapper around the CDF object.
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
# pylint: disable=too-many-arguments

from numpy import broadcast_to, asarray, argsort, searchsorted, arange
from vires.cdf_util import (
    cdf_open, datetime_to_cdf_rawtime, cdf_type_map,
    convert_cdf_raw_times, CDF_EPOCH_TYPE, CDF_TIME_TYPES,
)
from vires.dataset import Dataset

SLICE_ALL = slice(None)


class CDFDataset:
    """ Convenience wrapper around the CDF object. """

    def __init__(self, filename, translation=None, time_type=CDF_EPOCH_TYPE):
        self.cdf = None
        self.open(filename)
        # variable name translation
        self._translation = translation or {}
        self._time_type = time_type

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def open(self, filename):
        """ Open CDF file. """
        self.close()
        self.cdf = cdf_open(filename)

    def close(self):
        """ Close CDF file. """
        if self.cdf is not None:
            self.cdf.close()
            self.cdf = None

    def get_temporal_subset(self, time_variable, start, stop, subset=None,
                            is_sorted=False, second_time_variable=None,
                            max_record_duration=None):
        """ Extract temporal subset and NVR shape. """

        common_options = {
            "start": start,
            "stop": stop,
            "subset": subset,
            "is_sorted": is_sorted,
        }

        if second_time_variable is None:
            return self._get_temporal_subset(
                time_variable=time_variable,
                **common_options,
            )

        return self._get_temporal_interval_subset(
            start_time_variable=time_variable,
            end_time_variable=second_time_variable,
            max_record_duration=max_record_duration,
            **common_options,
        )

    def _get_temporal_subset(self, time_variable, start, stop, subset=None,
                            is_sorted=False):
        """ Extract temporal subset and NVR shape. """

        times, cdf_variable = self._extract_variable(time_variable)
        times, time_type = self._convert_time(times, cdf_variable.type())

        # empty dataset
        if times.size == 0:
            return slice(0, 0), (0,)

        extract_subset = (
            self._extract_subset_sorted if is_sorted else
            self._extract_subset_unsorted
        )

        time_bounds = [
            datetime_to_cdf_rawtime(start, time_type),
            datetime_to_cdf_rawtime(stop, time_type),
        ]

        if subset is None:
            # selecting from all times
            return extract_subset(times, time_bounds)

        # selecting from a time subset
        index = arange(times.size)[subset]
        subset, nrv_shape = extract_subset(times[index], time_bounds)
        return index[subset], nrv_shape

    def _get_temporal_interval_subset(self, start_time_variable,
                                     end_time_variable, max_record_duration,
                                     start, stop, subset=None, is_sorted=False):
        """ Extract temporal subset and NVR shape for time-interval records. """

        def _get_times_and_type(time_variable):
            times, cdf_variable = self._extract_variable(time_variable)
            return self._convert_time(times, cdf_variable.type())

        start_times, start_time_type = _get_times_and_type(start_time_variable)
        end_times, end_time_type = _get_times_and_type(end_time_variable)

        if start_times.shape != end_times.shape:
            raise ValueError(
                f"{start_time_variable} and {end_time_variable} values "
                "must be of the same shape!"
            )

        if max_record_duration is None:
            raise ValueError("Missing mandatory maximum record duration.")

        # empty dataset
        if start_times.size == 0:
            return slice(0, 0), (0,)

        # time bounds
        min_start_time = (
            start_times.min() if max_record_duration is None else
            datetime_to_cdf_rawtime(start - max_record_duration, start_time_type)
        )
        max_start_time = datetime_to_cdf_rawtime(stop, start_time_type)
        min_end_time = datetime_to_cdf_rawtime(start, end_time_type)

        # initial raw subset extracted from start time

        extract_subset = (
            self._extract_subset_sorted if is_sorted else
            self._extract_subset_unsorted
        )

        if subset is None:
            # selecting from all times
            subset, _ = extract_subset(start_times, [min_start_time, max_start_time])
        else:
            # selecting from a time subset
            index = arange(start_times.size)[subset]
            subset, _ = extract_subset(start_times[index], [min_start_time, max_start_time])
            subset = index[subset]

        # refined subset extracted from end time

        index = arange(end_times.size)[subset]
        subset = index[end_times[index] >= min_end_time]
        nrv_shape = subset.shape

        return subset, nrv_shape

    @staticmethod
    def _extract_subset_sorted(times, time_bounds):
        index_low, index_high = searchsorted(times, time_bounds, 'left')
        subset = slice(index_low, index_high)
        nrv_shape = (index_high - index_low,)
        return subset, nrv_shape

    @staticmethod
    def _extract_subset_unsorted(times, time_bounds):
        index = times.argsort(kind="stable")
        index_low, index_high = searchsorted(times[index], time_bounds, 'left')
        subset = index[index_low:index_high]
        nrv_shape = subset.shape
        return subset, nrv_shape

    def extract_datset(self, variables, subset=Ellipsis, nrv_shape=None,
                       ignored_variables=()):
        """ Extract dataset from a product. """
        subset1, subset2 = self._parse_subset(subset)
        dataset = Dataset()
        for variable in variables:
            if variable in ignored_variables:
                continue
            data, cdf_variable = self._extract_variable(
                variable, subset1, subset2, nrv_shape
            )
            if cdf_variable.rv() and nrv_shape is None:
                nrv_ndim = max(0, data.ndim - cdf_variable.ndim - 1)
                nrv_shape = data.shape[:nrv_ndim]
            cdf_type = cdf_type_map(cdf_variable.type())
            if cdf_type in CDF_TIME_TYPES:
                data, cdf_type = self._convert_time(data, cdf_type)
            dataset.set(variable, data, cdf_type, cdf_variable.attrs)
        return dataset

    def extact_variable(self, variable, subset=Ellipsis, nrv_shape=None):
        """ Extract variable with optional subset along the first dimension
        (regular variable) and broadcast shape for NRV variables.
        """
        subset1, subset2 = self._parse_subset(subset)
        data, cdf_variable = self._extract_variable(
            variable, subset1, subset2, nrv_shape
        )
        return data, cdf_variable

    def _extract_variable(self, variable, subset1=SLICE_ALL, subset2=SLICE_ALL,
                          nrv_shape=None):
        """ Low-level variable extaction. """
        cdf_variable = self.cdf.raw_var(
            self._translation.get(variable, variable)
        )
        if cdf_variable.rv(): # regular variable
            data = cdf_variable[subset1, ...][subset2, ...]
        else: # NRV variable
            data = asarray(cdf_variable[...])
            if nrv_shape:
                data = broadcast_to(data, (*nrv_shape, *data.shape))
        return data, cdf_variable

    @staticmethod
    def _parse_subset(subset):
        """ Parse record subset specification and split into two selections
        compatible with the CDF library slicing.
        """
        if subset is Ellipsis or subset is None:
            return SLICE_ALL, SLICE_ALL

        if isinstance(subset, slice):
            return subset, SLICE_ALL

        # else assuming index
        index = asarray(subset)

        if index.size != 0:
            index_min, index_max = index.min(), index.max() + 1
        else:
            index_min, index_max =  0, 0

        if index_min != 0:
            index = index - index_min

        return slice(index_min, index_max), index

    def _convert_time(self, times, cdf_type):
        """ Convert times to the expected time data type. """
        return (
            convert_cdf_raw_times(times, cdf_type, self._time_type),
            self._time_type
        )
