#-------------------------------------------------------------------------------
#
# Data Source - quasi-dipole coordinates and magnetic local time
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
#pylint: disable=too-many-locals

from logging import getLogger, LoggerAdapter
from numpy import hstack
from eoxmagmod.qd import eval_qdlatlon_with_base_vectors, eval_mlt
from vires.util import include, unique
from vires.cdf_util import (
    cdf_rawtime_to_mjd2000,
    cdf_rawtime_to_datetime,
    cdf_rawtime_to_decimal_year_fast,
    CDF_DOUBLE_TYPE,
)
from vires.dataset import Dataset
from .model import Model


class QuasiDipoleCoordinates(Model):
    """ Magnetic Quasi-Dipole coordinates model. """
    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "Latitude", "Longitude", "Radius",
    ]
    DEFAULT_OUTPUT_VARIABLES = ["QDLat", "QDLon", "QDBasis"]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'QDLatLon: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        varmap = varmap or {}
        self.qdlat_variable, self.qdlon_variable, self.basis_variable = (
            self.DEFAULT_OUTPUT_VARIABLES
        )
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    @property
    def required_variables(self):
        return self._required_variables

    @property
    def variables(self):
        return [self.qdlat_variable, self.qdlon_variable, self.basis_variable]

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        if variables:
            self.logger.debug("requested dataset length %s", dataset.length)
            # extract input data
            times, lats, lons, rads = (
                dataset[var] for var in self.required_variables
            )
            cdf_type = dataset.cdf_type.get(self.required_variables[0], None)
            if times.size > 0:
                year = cdf_rawtime_to_datetime(times[0], cdf_type).year
            else:
                year = 2000 # default if not time-stamp value is available
            # evaluate quasi-dipole coordinates
            qdlat, qdlon, f11, f12, f21, f22, _ = eval_qdlatlon_with_base_vectors(
                lats, lons, rads * 1e-3, # radius in km
                cdf_rawtime_to_decimal_year_fast(times, cdf_type, year)
            )
            if self.qdlat_variable in variables:
                output_ds.set(self.qdlat_variable, qdlat, CDF_DOUBLE_TYPE, {
                    'DESCRIPTION': 'Magnetic quasi-dipole latitude',
                    'UNITS': 'deg'
                })
            if self.qdlon_variable in variables:
                output_ds.set(self.qdlon_variable, qdlon, CDF_DOUBLE_TYPE, {
                    'DESCRIPTION': 'Magnetic quasi-dipole longitude',
                    'UNITS': 'deg'
                })
            if self.basis_variable in variables:
                size = times.size
                output_ds.set(
                    self.basis_variable,
                    hstack((
                        f11.reshape((size, 1)),
                        f12.reshape((size, 1)),
                        f21.reshape((size, 1)),
                        f22.reshape((size, 1)),
                    )).reshape((size, 2, 2,)),
                    CDF_DOUBLE_TYPE,
                    {'DESCRIPTION': 'QD vector basis [F1, F2]', 'UNITS': '-'}
                )

        return output_ds


class MagneticLocalTime(Model):
    """ Magnetic Local Time model. """
    DEFAULT_REQUIRED_VARIABLES = ["Timestamp", "QDLon"]
    DEFAULT_OUTPUT_VARIABLE = "MLT"

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'MLT: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        varmap = varmap or {}
        self.output_variable = self.DEFAULT_OUTPUT_VARIABLE
        self.time_variable, self.qdlon_variable = (
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        )
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    @property
    def required_variables(self):
        return [self.time_variable, self.qdlon_variable]

    @property
    def variables(self):
        return [self.output_variable]

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        proceed = variables is None or self.output_variable in variables
        self.logger.debug(
            "requested variables %s", self.variables if proceed else []
        )
        if proceed:
            self.logger.debug("requested dataset length %s", dataset.length)
            cdf_type = dataset.cdf_type.get(self.time_variable)
            output_ds.set(
                self.output_variable, eval_mlt(
                    dataset[self.qdlon_variable],
                    cdf_rawtime_to_mjd2000(
                        dataset[self.time_variable], cdf_type
                    ),
                ),
                CDF_DOUBLE_TYPE,
                {'DESCRIPTION': 'Magnetic local time', 'UNITS': 'h'}
            )
        return output_ds
