#-------------------------------------------------------------------------------
#
# Data Source - quasi-dipole coordinates and magnetic local time
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
#pylint: disable=too-many-locals,missing-docstring

from logging import getLogger, LoggerAdapter
from numpy import stack
from eoxmagmod import (
    eval_qdlatlon_with_base_vectors, eval_mlt, mjd2000_to_decimal_year,
)
from vires.util import include, unique
from vires.cdf_util import cdf_rawtime_to_mjd2000, CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class QuasiDipoleCoordinates(Model):
    """ Magnetic Quasi-Dipole coordinates model. """
    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "Latitude", "Longitude", "Radius",
    ]

    VARIABLES = {
        "QDLat": {
            'DESCRIPTION': 'Magnetic quasi-dipole latitude',
            'UNITS': 'deg'
        },
        "QDLon": {
            'DESCRIPTION': 'Magnetic quasi-dipole longitude',
            'UNITS': 'deg'
        },
        "QDBasis": {
            'DESCRIPTION': 'QD vector basis [F1, F2]',
            'UNITS': '-'
        },
    }

    @property
    def variables(self):
        return ["QDLat", "QDLon", "QDBasis"]

    @property
    def required_variables(self):
        return list(self._required_variables)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'QDLatLon: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super(QuasiDipoleCoordinates, self).__init__()
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def _extract_required_variables(self, dataset):
        time, latitude, longitude, radius = self._required_variables
        # Note: radius is converted from metres to kilometres
        return (
            cdf_rawtime_to_mjd2000(dataset[time], dataset.cdf_type[time]),
            dataset[latitude], dataset[longitude], 1e-3*dataset[radius],
        )

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        if variables:
            self.logger.debug("requested dataset length %s", dataset.length)

            times, lats, lons, rads = self._extract_required_variables(dataset)

            # evaluate quasi-dipole coordinates
            qdlat, qdlon, f11, f12, f21, f22, _ = eval_qdlatlon_with_base_vectors(
                lats, lons, rads, mjd2000_to_decimal_year(times)
            )

            def _set_output(variable, data):
                output_ds.set(
                    variable, data, CDF_DOUBLE_TYPE, self.VARIABLES[variable]
                )

            qdlat_variable, qdlon_variable, basis_variable = self.variables

            if qdlat_variable in variables:
                _set_output(qdlat_variable, qdlat)

            if qdlon_variable in variables:
                _set_output(qdlon_variable, qdlon)

            if basis_variable in variables:
                _set_output(basis_variable, stack(
                    (f11, f12, f21, f22), axis=1
                ).reshape((f11.size, 2, 2,)))

        return output_ds


class MagneticLocalTime(Model):
    """ Magnetic Local Time model. """
    DEFAULT_REQUIRED_VARIABLES = ["Timestamp", "QDLon"]

    VARIABLE = "MLT"
    ATTRIB = {
        'DESCRIPTION': 'Magnetic local time',
        'UNITS': 'h',
    }

    @property
    def variables(self):
        return [self.VARIABLE]

    @property
    def required_variables(self):
        return list(self._required_variables)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'MLT: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super(MagneticLocalTime, self).__init__()
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def _extract_required_variables(self, dataset):
        time, qdlon = self._required_variables
        return (
            cdf_rawtime_to_mjd2000(dataset[time], dataset.cdf_type[time]),
            dataset[qdlon],
        )

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variable = self.VARIABLE
        proceed = variables is None or variable in variables
        self.logger.debug(
            "requested variables %s", self.variables if proceed else []
        )

        if proceed:
            self.logger.debug("requested dataset length %s", dataset.length)
            times, qdlons = self._extract_required_variables(dataset)
            mlt = eval_mlt(qdlons, times)
            output_ds.set(variable, mlt, CDF_DOUBLE_TYPE, self.ATTRIB)

        return output_ds
