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
from numpy import stack
from eoxmagmod import vnorm
from vires.util import include, unique
from vires.cdf_util import cdf_rawtime_to_mjd2000, CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .model import Model


class MagneticModelResidual(Model):
    """ Residual evaluation. """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["residual_name"], msg), kwargs

    def __init__(self, model_name, variable, logger=None):
        self.model_name = model_name
        self._required_variables = [variable, "%s_%s" % (variable, model_name)]
        self.variable = variable
        self.model_variable = "%s_%s" % (variable, model_name)
        self.output_variable = "%s_res_%s" % (variable, model_name)
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "residual_name": self.output_variable,
        })

    @property
    def variables(self):
        return [self.output_variable]

    @property
    def required_variables(self):
        return [self.variable, self.model_variable]

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        proceed = variables is None or self.output_variable in variables
        self.logger.debug(
            "requested variables %s", self.variables if proceed else []
        )
        if proceed:
            self.logger.debug("requested dataset length %s", dataset.length)
            output_ds.set(
                self.output_variable,
                dataset[self.variable] - dataset[self.model_variable],
                dataset.cdf_type[self.variable],
                self._get_attributes(dataset, self.variable),
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
    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "Latitude", "Longitude", "Radius",
    ]
    BASE_VARIABLES = ["F", "B_NEC"]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["model_name"], msg), kwargs

    def __init__(self, model_name, model, logger=None, varmap=None):
        self.name = model_name
        self.model = model
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self._provided_variables = [
            "%s_%s" % (variable, model_name) for variable in self.BASE_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": model_name,
        })
        self.attrib = self._variable_attributes()

    def _variable_attributes(self):
        f_var, b_var = self.variables
        return {
            f_var: {
                'DESCRIPTION': (
                    'Magnetic field intensity, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            },
            b_var: {
                'DESCRIPTION': (
                    'Magnetic field vector, NEC frame, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            },
        }

    @property
    def variables(self):
        return self._provided_variables

    @property
    def required_variables(self):
        return self._required_variables

    def _extract_required_variables(self, dataset):
        time, latitude, longitude, radius = self._required_variables
        # Note: radius is converted from metres to kilometres
        return (
            cdf_rawtime_to_mjd2000(dataset[time], dataset.cdf_type[time]),
            dataset[latitude], dataset[longitude], 1e-3*dataset[radius],
        )

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        output_ds = Dataset()

        if variables:
            times, lats, lons, rads = self._extract_required_variables(dataset)

            result = self.model.eval(
                times, stack((lats, lons, rads), axis=1), scale=[1, 1, -1]
            )

            f_var, b_var = self.variables
            if f_var in variables:
                output_ds.set(
                    f_var, vnorm(result), CDF_DOUBLE_TYPE, self.attrib[f_var]
                )
            if b_var in variables:
                output_ds.set(
                    b_var, result, CDF_DOUBLE_TYPE, self.attrib[b_var]
                )

        return output_ds
