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
from vires.aux_kp import query_kp, query_kp_int
from vires.aux_dst import query_dst, query_dst_int
from vires.aux_f107 import (
    FIELD_TIME as FIELD_F107_TIME, FIELD_F107,
    query_aux_f107_2_, query_aux_f107_2__int,
)
from vires.dataset import Dataset
from .time_series import TimeSeries
from .model import Model


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

    def __init__(self, name, filename, query_fcn, iterp_fcn, varmap,
                 logger=None):
        self._name = name
        self._filename = filename
        self._query = query_fcn
        self._interp = iterp_fcn
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
            src_data = self._query(self._filename, start, stop, fields=tuple(
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
            src_data = self._interp(
                self._filename, self._encode_time(times, cdf_type),
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


class IndexKp10(AuxiliaryDataTimeSeries):
    """ Kp10 index time-series source class. """
    CDF_TYPE = {
        'Timestamp': CDF_EPOCH_TYPE,
        'Kp10': CDF_UINT2_TYPE,
    }
    CDF_INTERP_TYPE = {'Kp': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'Kp10': {
            'DESCRIPTION': 'Global geo-magnetic storm index multiplied by 10.',
            'UNITS': '-',
        },
    }

    def __init__(self, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, "Kp10", filename, query_kp, query_kp_int,
            {'time': 'Timestamp', 'kp': 'Kp10'}, logger
        )



class IndexKpFromKp10(Model):
    """ Conversion of Kp10 to Kp.
    """
    REQUIRED_VARIABLE = "Kp10"
    PROVIDED_VARIABLE = "Kp"
    CDF_VARIABLE = (
        CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Global geo-magnetic storm index.',
            'UNITS': '-',
        }
    )

    @property
    def variables(self):
        return [self.PROVIDED_VARIABLE]

    @property
    def required_variables(self):
        return [self._required_variable]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'KpFromKp10: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        varmap = varmap or {}
        self._required_variable = varmap.get(
            self.REQUIRED_VARIABLE, self.REQUIRED_VARIABLE
        )
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        required_variable = self._required_variable
        provided_variable = self.PROVIDED_VARIABLE

        eval_kp = variables is None or provided_variable in variables

        self.logger.debug(
            "requested variables: %s", required_variable if eval_kp else ""
        )

        if eval_kp:
            output_ds.set(
                provided_variable, 0.1*dataset[required_variable],
                *self.CDF_VARIABLE
            )

        return output_ds


class IndexDst(AuxiliaryDataTimeSeries):
    """ Dst index time-series source class. """
    CDF_TYPE = {'Timestamp': CDF_EPOCH_TYPE, 'Dst': CDF_DOUBLE_TYPE}
    CDF_INTERP_TYPE = {'Dst': CDF_DOUBLE_TYPE}
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


class IndexF107(AuxiliaryDataTimeSeries):
    """ F10.7 index (AUX_F10_2_) time-series source class. """
    CDF_TYPE = {'Timestamp': CDF_EPOCH_TYPE, 'F107': CDF_DOUBLE_TYPE}
    CDF_INTERP_TYPE = {'F107': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'F107': {
            'DESCRIPTION': 'Assembled daily observed values of solar flux F10.7',
            'UNITS': '10e-22 W m^-2 Hz^-1',
        },
    }

    def __init__(self, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, "F107", filename,
            query_aux_f107_2_, query_aux_f107_2__int,
            {FIELD_F107_TIME: 'Timestamp', FIELD_F107: 'F107'}, logger
        )
