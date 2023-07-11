#-------------------------------------------------------------------------------
#
# Data Source - base time-series class
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
# pylint: disable=too-many-arguments

from numpy import asarray
from vires.cdf_util import (
    CDF_EPOCH_TYPE,
    mjd2000_to_cdf_rawtime,
    convert_cdf_raw_times,
)
from vires.util import include, unique


class TimeSeries():
    """ Base time-series data source class. """

    TIMESTAMP_TYPE = CDF_EPOCH_TYPE

    def __init__(self):
        self.product_set = set() # stores all recorded source products

    @property
    def products(self):
        """ Get list of all accessed products. """
        return list(self.product_set)

    @property
    def variables(self):
        """ Get list of the provided variables. """
        raise NotImplementedError

    @property
    def required_variable(self):
        """ Get the input dataset variable required by the slave time-series.
        """
        return "Timestamp"

    def get_extracted_variables(self, variables):
        """ Expand/filter input variables into applicable variables. """
        if variables is None:
            return self.variables # get all available variables

        # get an applicable subset of the requested variables
        return list(include(unique(variables), self.variables))

    def subset(self, start, stop, variables=None):
        """ Generate a sequence of datasets holding the requested temporal
        subset of the time-series.
        Optionally, the returned variables can be restricted by the user defined
        list of variables.
        The start and stop UTC times should be instances of the
        datetime.datetime object.
        The output time-stamps are encoded as CDF-epoch times.
        """
        raise NotImplementedError

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=TIMESTAMP_TYPE, valid_only=False):
        """ Get time-series interpolated from the provided time-line.
        Optionally, the returned variables can be restricted by the user defined
        list of variables.
        The default nearest neighbour interpolation method is used to
        interpolate the variables. Alternative interpolation methods
        can be specified for selected variables via the interp1d_kinds
        dictionary.
        Set valid_only to True to remove invalid records (NaNs due to the
        out-of-bounds interpolation).
        The input and output time-stamps are encoded as CDF-epoch times.

        If cdf_type set to None, the time values are reinterpreted as
        MJD2000 values.
        """
        raise NotImplementedError

    @staticmethod
    def _convert_time(times, cdf_type, target_cdf_type=TIMESTAMP_TYPE):
        # handle scalar input
        times = asarray(times)
        if times.ndim == 0:
            times = times.reshape(1)

        if cdf_type != target_cdf_type:
            if cdf_type is None:
                times = mjd2000_to_cdf_rawtime(times, target_cdf_type)
            else:
                times = convert_cdf_raw_times(times, cdf_type, target_cdf_type)

        return times, target_cdf_type

    def __str__(self):
        name = self.__class__.__name__
        inputs = self.required_variable
        outputs = ",".join(self.variables)
        return f"{name}([{inputs}] -> [{outputs}])"
