#-------------------------------------------------------------------------------
#
# VirES HAPI - data reader
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

from numpy import asarray, broadcast_to, searchsorted
from vires.time_util import datetime_to_datetime64
from vires.cdf_util import cdf_open, CDF_EPOCH_TYPE, cdf_rawtime_to_datetime64
from vires.dataset import Dataset
from ..data_type import parse_data_type, TIME_PRECISION


class CdfTimeSeriesReader():
    """ CDF file time-series reader. """
    CHUNK_SIZE = 10800 # equivalent of 3h of 1Hz data

    def __init__(self, start, stop, extracted_parameters,
                 time_parameter="Timestamp", time_parameter_options=None):

        self._start_time = datetime_to_datetime64(start)
        self._stop_time = datetime_to_datetime64(stop)
        self._time_parameter = (
            time_parameter,
            time_parameter_options or extracted_parameters[time_parameter]
        )
        self._extracted_parameters = list(extracted_parameters.items())


    def __call__(self, source):
        start_index, stop_index = source.get('indexRange') or (0, None)

        if source.get("isSorted", True):
            extract_time_subset = self._subset_sorted
        else:
            extract_time_subset = self._subset_unsorted

        with cdf_open(source['location']) as cdf:
            size, slice_, subset = extract_time_subset(
                self._read_variable(cdf, *self._time_parameter),
                self._start_time, self._stop_time,
                start_index, stop_index,
            )
            yield from self._read_subsets(
                cdf, size, slice_, subset, self._extracted_parameters
            )

    @staticmethod
    def _subset_sorted(values, start_value, stop_value, start_index, stop_index):
        """ Extract slice selecting items of a sorted 1D array within
        the given bounds:
            start_value <= value < stop_value
            start_index <= index < stop_index
        """
        start, stop = searchsorted(
            values[start_index:stop_index], [start_value, stop_value], 'left'
        )
        start, stop = start + start_index, stop + start_index
        return stop - start, slice(start, stop), Ellipsis

    @staticmethod
    def _subset_unsorted(values, start_value, stop_value, start_index, stop_index):
        """ Extract slice selecting items of an unsorted 1D array within
        the given bounds:
            start_value <= value < stop_value
            start_index <= index < stop_index
        """
        index = values[start_index:stop_index].argsort(kind='stable')
        if start_index > 0:
            index += start_index
        start, stop = searchsorted(values[index], [start_value, stop_value], 'left')
        index = index[start:stop]
        if index.size == 0:
            return 0, slice(0, 0), Ellipsis
        return index.size, slice(index.min(), index.max() + 1), index - start

    @classmethod
    def _read_subsets(cls, cdf, size, slice_, subset, extracted_parameters):
        """ Yield chunks of the selected data. """
        dataset = cls._read_subset(cdf, size, slice_, subset, extracted_parameters)
        size = dataset.length
        for idx_start in range(0, size, cls.CHUNK_SIZE):
            idx_stop = min(idx_start + cls.CHUNK_SIZE, size)
            yield dataset.subset(slice(idx_start, idx_stop))

    @classmethod
    def _read_subset(cls, cdf, size, slice_, subset, extracted_parameters):
        """ Read subset of a CDF file into a Dataset object. """
        dataset = Dataset()
        for variable, options in extracted_parameters:
            dataset.set(variable, cls._read_variable(
                cdf, variable, options, size=size, slice_=slice_, subset=subset
            ))
        return dataset

    @classmethod
    def _read_variable(cls, cdf, variable, options, size=None,
                       slice_=Ellipsis, subset=Ellipsis):
        """ Read subset of a CDF file variable. """
        source_variable = options.get("source") or variable
        cdf_var = cdf.raw_var(source_variable)
        cdf_type = cdf_var.type()
        if cdf_var.rv(): # regular record variable
            data = cls._parse_data(cdf_type, cdf_var[slice_][subset], options)
        else:
            # NRV variable - requires size to be set
            value = cls._parse_data(cdf_type, asarray(cdf_var[...]), options)
            data = broadcast_to(value, (size,) + value.shape)
        cls._assert_declared_type(variable, data, options)
        return data

    @staticmethod
    def _assert_declared_type(variable, data, options):
        """ Assert that the extracted data type matches the data type declared
        in parameter's metadata.
        """
        declared = parse_data_type(options)
        if data.dtype != declared.dtype:
            raise AssertionError(
                f"{variable}: mismatch between the declared and extracted "
                f"data type! {declared.dtype} != {data.dtype}"
            )

    @staticmethod
    def _parse_data(cdf_type, raw_data, options):
        """ Covert raw CDF data into a native Numpy format. """
        if cdf_type == CDF_EPOCH_TYPE:
            unit = TIME_PRECISION[options.get("timePrecision")]
            return cdf_rawtime_to_datetime64(raw_data, cdf_type, unit=unit)
        return raw_data
