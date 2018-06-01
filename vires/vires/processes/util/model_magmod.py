#-------------------------------------------------------------------------------
#
# Data Source - magnetic model
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
from itertools import chain
from numpy import stack
from eoxmagmod import vnorm
from vires.util import include, unique, cached_property
from vires.cdf_util import cdf_rawtime_to_mjd2000, CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .model import Model


class MagneticModelResidual(Model):
    """ Residual evaluation. """

    @cached_property
    def variables(self):
        return ["%s_res_%s" % (self.variable, self.model_name)]

    @cached_property
    def required_variables(self):
        return [self.variable, "%s_%s" % (self.variable, self.model_name)]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["residual_name"], msg), kwargs

    def __init__(self, model_name, variable, logger=None):
        self.model_name = model_name
        self.variable = variable
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "residual_name": self.variables[0],
        })

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        output_variable, = self.variables
        is_requested = variables is None or output_variable in variables
        self.logger.debug(
            "requested variables %s", self.variables if is_requested else []
        )
        if is_requested:
            self.logger.debug("requested dataset length %s", dataset.length)
            measurement_variable, model_variable = self.required_variables
            output_ds.set(
                output_variable,
                dataset[measurement_variable] - dataset[model_variable],
                dataset.cdf_type[measurement_variable],
                self._get_attributes(dataset, measurement_variable),
            )
        return output_ds

    def _get_attributes(self, dataset, variable):
        src_attr = dataset.cdf_attr.get(variable)
        if not src_attr:
            return None

        if variable == "B_NEC":
            base = 'Magnetic field vector residual, NEC frame'
        else:
            base = "%s residual" % src_attr['DESCRIPTION']

        return {
            'DESCRIPTION': (
                '%s, calculated as a difference of the measurement and '
                'value of the %s spherical harmonic model' %
                (base, self.model_name)
            ),
            'UNITS': src_attr['UNITS']
        }


class MagneticModel(Model):
    """ Forward spherical expansion model. """
    SOURCE_VARIABLES = {
        "time": ["Timestamp"],
        "location": ["Latitude", "Longitude", "Radius"],
        "f107": ["F107"],
        "subsolar_point": ["SunDeclination", "SunLongitude"]
    }
    BASE_VARIABLES = ["F", "B_NEC"]

    @cached_property
    def variables(self):
        model_name = self.name
        return [
            "%s_%s" % (variable, model_name) for variable in self.BASE_VARIABLES
        ]

    @cached_property
    def required_variables(self):
        return list(chain.from_iterable(
            variables for variables in self._source_variables.values()
        ))

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["model_name"], msg), kwargs

    def __init__(self, model_name, model, logger=None, varmap=None):
        self.name = model_name
        self.model = model
        varmap = varmap or {}

        available_data_extractors = {
            "time": self._extract_time,
            "location": self._extract_location,
            "f107": self._extract_f107,
            "subsolar_point": self._extract_subsolar_point,
        }

        self.data_extractors = [
            available_data_extractors[requirement]
            for requirement in model.parameters
        ]

        self._source_variables = {
            requirement: [
                varmap.get(var, var) for var
                in self.SOURCE_VARIABLES[requirement]
            ]
            for requirement in model.parameters
        }

        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": model_name,
        })

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        output_ds = Dataset()

        if variables:
            inputs = {"scale": [1, 1, -1]}
            for extract in self.data_extractors:
                inputs.update(extract(dataset))

            result = self.model.eval(**inputs)

            for variable in variables:
                filter_, type_, attrib = self.output[variable]
                output_ds.set(variable, filter_(result), type_, attrib)

        return output_ds

    @cached_property
    def output(self):
        f_var, b_var = self.variables
        return {
            f_var: (vnorm, CDF_DOUBLE_TYPE, {
                'DESCRIPTION': (
                    'Magnetic field intensity, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            }),
            b_var: (lambda r: r, CDF_DOUBLE_TYPE, {
                'DESCRIPTION': (
                    'Magnetic field vector, NEC frame, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            }),
        }

    def _extract_time(self, dataset):
        time, = self._source_variables["time"]
        return [
            ("time", cdf_rawtime_to_mjd2000(
                dataset[time], dataset.cdf_type[time]
            )),
        ]

    def _extract_location(self, dataset):
        latitude, longitude, radius = self._source_variables["location"]
        return [
            ("location", stack((
                # Note: radius is converted from metres to kilometres
                dataset[latitude], dataset[longitude], 1e-3*dataset[radius],
            ), axis=1)),
        ]

    def _extract_f107(self, dataset):
        f107, = self._source_variables["f107"]
        return [
            ("f107", dataset[f107]),
        ]

    def _extract_subsolar_point(self, dataset):
        lat_sol, lon_sol = self._source_variables["subsolar_point"]
        return [
            ("lat_sol", dataset[lat_sol]),
            ("lon_sol", dataset[lon_sol]),
        ]
