#-------------------------------------------------------------------------------
#
# Data Source - base auxiliary data time-series class
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
#pylint: disable=too-many-arguments,missing-docstring

from logging import getLogger, LoggerAdapter
from numpy import array, empty
from vires.util import include
from vires.cdf_util import (
    mjd2000_to_cdf_rawtime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_datetime,
    CDF_EPOCH_TYPE, CDF_DOUBLE_TYPE,
)
from vires.dataset import Dataset
from .base import TimeSeries


class AuxiliaryDataTimeSeries(TimeSeries):
    """ Auxiliary data time-series class. """
    CDF_TYPE = {}
    CDF_INTERP_TYPE = {}
    CDF_ATTR = {}
    DATA_CONVERSION = {}
    TIME_VARIABLE = "Timestamp"

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["index_name"], msg), kwargs

    @staticmethod
    def _encode_time(times, cdf_type):
        """ Convert the raw CDF time to the time format of the dataset. """
        return cdf_rawtime_to_mjd2000(times, cdf_type)

    @staticmethod
    def _decode_time(times, cdf_type):
        """ Convert the time format of the dataset to the raw CDF time. """
        return mjd2000_to_cdf_rawtime(times, cdf_type)

    def __init__(self, name, filename, reader_factory, varmap,
                 logger=None):
        super(AuxiliaryDataTimeSeries, self).__init__()
        self._name = name
        self._filename = filename
        self._reader = reader_factory(filename, self.product_set)
        self._varmap = varmap
        self._revvarmap = dict((val, key) for key, val in varmap.items())
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "index_name": name,
        })

    @property
    def variables(self):
        return self._varmap.values()

    def subset(self, start, stop, variables=None):
        variables = self.get_extracted_variables(variables)
        self.logger.debug("subset: %s %s", start, stop)
        self.logger.debug("variables: %s", variables)
        dataset = Dataset()
        if variables:
            src_data = self._reader.subset(start, stop, fields=tuple(
                self._revvarmap[variable] for variable in variables
            ))
            for src_var, data in src_data.items():
                variable = self._varmap[src_var]
                cdf_type = self.CDF_TYPE.get(variable)
                cdf_attr = self.CDF_ATTR.get(variable)
                if variable == self.TIME_VARIABLE:
                    data = self._decode_time(data, cdf_type)
                dataset.set(variable, data, cdf_type, cdf_attr)

        self.logger.debug("dataset length: %s", dataset.length)
        return dataset

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=CDF_EPOCH_TYPE, valid_only=False):
        times, cdf_type = self._convert_time(times, cdf_type)

        if times.size == 0: # return an empty dataset
            dataset = Dataset()
            for variable in self.get_extracted_variables(variables):
                dataset.set(
                    variable, empty(0),
                    self.CDF_TYPE.get(variable),
                    self.CDF_ATTR.get(variable)
                )
            return dataset

        variables = list(
            include(variables, self.variables) if variables is not None else
            self.variables
        )
        dependent_variables = [
            variable for variable in variables if variable != self.TIME_VARIABLE
        ]
        self.logger.debug(
            "requested time-span %s, %s",
            cdf_rawtime_to_datetime(times.min(), cdf_type),
            cdf_rawtime_to_datetime(times.max(), cdf_type)
        )
        self.logger.debug("requested dataset length %s", times.size)
        self.logger.debug("variables: %s", variables)
        dataset = Dataset()
        if self.TIME_VARIABLE in variables:
            dataset.set(
                self.TIME_VARIABLE, array(times), cdf_type,
                self.CDF_ATTR.get(self.TIME_VARIABLE),
            )
        if dependent_variables:
            src_data = self._reader.interpolate(
                self._encode_time(times, cdf_type),
                fields=tuple(
                    self._revvarmap[variable] for variable in dependent_variables
                )
            )
            for src_var, data in src_data.items():
                variable = self._varmap[src_var]
                convert = self.DATA_CONVERSION.get(variable)
                if convert:
                    data = convert(data)
                dataset.set(
                    variable, data,
                    self.CDF_INTERP_TYPE.get(variable, CDF_DOUBLE_TYPE),
                    self.CDF_ATTR.get(variable),
                )
        self.logger.debug("interpolated dataset length: %s ", dataset.length)
        return dataset
