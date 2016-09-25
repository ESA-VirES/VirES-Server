#-------------------------------------------------------------------------------
#
# Data Source - auxiliary indices time-series class
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
#pylint: disable=too-many-arguments
# TODO: replace query_* and query_*_int functions

from logging import getLogger, LoggerAdapter
from numpy import array, empty
from vires.util import include
from vires.cdf_util import (
    mjd2000_to_cdf_rawtime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_datetime,
    CDF_EPOCH_TYPE, CDF_DOUBLE_TYPE, CDF_UINT2_TYPE,
)
from vires.aux import (
    query_dst, query_dst_int,
    query_kp, query_kp_int,
)
from .dataset import Dataset
from .time_series import TimeSeries


class AuxiliaryDataTimeSeries(TimeSeries):
    """ Auxiliary data time-series class. """
    CDF_TYPE = {}
    CDF_ATTR = {}
    TIME_VARIABLE = "Timestamp"

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["index_name"], msg), kwargs

    def __init__(self, name, filename, query_fcn, iterp_fcn, varmap,
                 logger=None):
        self._name = name
        self._filename = filename
        self._query = query_fcn
        self._interp = iterp_fcn
        self._varmap = varmap
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
            data_dict = self._query(self._filename, start, stop)
            for src_var, dst_var in self._varmap.items():
                if dst_var in variables:
                    data = data_dict[src_var]
                    cdf_type = self.CDF_TYPE.get(dst_var)
                    cdf_attr = self.CDF_ATTR.get(dst_var)
                    if dst_var == self.TIME_VARIABLE:
                        data = mjd2000_to_cdf_rawtime(data, cdf_type)
                    dataset.set(dst_var, data, cdf_type, cdf_attr)
        self.logger.debug("dataset length: %s", dataset.length)
        return dataset

    def interpolate(self, times, variables=None, interp1d_kinds=None,
                    cdf_type=CDF_EPOCH_TYPE, valid_only=False):
        # TODO: support for different CDF time types
        if cdf_type != CDF_EPOCH_TYPE:
            raise TypeError("Unsupported CDF time type %r !" % cdf_type)

        if len(times) == 0: # return an empty dataset
            return Dataset(
                (variable, empty(0))
                for variable in self.get_extracted_variables(variables)
            )

        variables = list(
            include(variables, self.variables) if variables is not None else
            self.variables
        )
        self.logger.debug(
            "requested time-span %s, %s",
            cdf_rawtime_to_datetime(min(times), cdf_type),
            cdf_rawtime_to_datetime(max(times), cdf_type)
        )
        self.logger.debug("requested dataset length %s", len(times))
        self.logger.debug("variables: %s", variables)
        dataset = Dataset()
        if self.TIME_VARIABLE in variables:
            dataset.set(
                self.TIME_VARIABLE, array(times), cdf_type,
                self.CDF_ATTR.get(self.TIME_VARIABLE),
            )
        if self._name in variables:
            src_var, data = self._interp(
                self._filename, cdf_rawtime_to_mjd2000(times, cdf_type)
            ).iteritems().next()
            dataset.set(
                self._varmap[src_var], data, CDF_DOUBLE_TYPE,
                self.CDF_ATTR.get(self._varmap[src_var]),
            )
        self.logger.debug("interpolated dataset length: %s ", dataset.length)
        return dataset


class IndexKp(AuxiliaryDataTimeSeries):
    """ Kp index time-series source class. """
    CDF_TYPE = {'Timestamp': CDF_EPOCH_TYPE, 'Kp': CDF_UINT2_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'Kp': {
            'DESCRIPTION': 'Global geo-magnetic storm index.',
            'UNITS': '-',
        },
    }

    def __init__(self, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, "Kp", filename, query_kp, query_kp_int,
            {'time': 'Timestamp', 'kp': 'Kp'}, logger
        )


class IndexDst(AuxiliaryDataTimeSeries):
    """ Dst index time-series source class. """
    CDF_TYPE = {'Timestamp': CDF_EPOCH_TYPE, 'Dst': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'Dst': {
            'DESCRIPTION': 'Disturbance storm time index',
            'UNITS': 'nT',
        },
    }

    def __init__(self, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, "Dst", filename, query_dst, query_dst_int,
            {'time': 'Timestamp', 'dst': 'Dst'}, logger
        )
