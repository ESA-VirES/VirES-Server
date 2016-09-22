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
from numpy import hstack
from eoxmagmod import vnorm, GEOCENTRIC_SPHERICAL
from vires.util import include, unique
from vires.time_util import datetime_mean, datetime_to_decimal_year
from vires.cdf_util import (
    cdf_rawtime_to_datetime,
    CDF_EPOCH_TYPE,
    CDF_DOUBLE_TYPE,
)
from .model import Model
from .dataset import Dataset


class MagneticModelResidual(Model):
    """ Residual evaluation. """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["residual_name"], msg), kwargs

    def __init__(self, model_name, variable, logger=None):
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
                dataset.cdf_type[self.variable]
            )
        return output_ds


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

    @property
    def variables(self):
        return self._provided_variables

    @property
    def required_variables(self):
        return self._required_variables

    def eval(self, dataset, variables=None, **kwargs):
        req_var = self.required_variables
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        output_ds = Dataset()
        if variables:
            # extract input data
            times, lats, lons, rads = (dataset[var] for var in req_var[:4])
            cdf_type = dataset.cdf_type.get(req_var[0], None)
            # TODO: support for different CDF time types
            if cdf_type != CDF_EPOCH_TYPE:
                raise TypeError("Unsupported CDF time type %r !" % cdf_type)

            start = cdf_rawtime_to_datetime(min(times), cdf_type)
            stop = cdf_rawtime_to_datetime(max(times), cdf_type)
            mean_time = datetime_mean(start, stop)
            mean_time_dy = datetime_to_decimal_year(mean_time)
            self.logger.debug("requested time-span %s, %s", start, stop)
            self.logger.debug("requested dataset length %s", len(times))
            self.logger.debug(
                "applied mean time %s (%s)", mean_time, mean_time_dy
            )
            # extract variable names
            # evaluate model
            model_data = self.model.eval(
                hstack((
                    lats.reshape((lats.size, 1)),
                    lons.reshape((lons.size, 1)),
                    rads.reshape((lons.size, 1)) * 1e-3, # radius in km
                )),
                mean_time_dy,
                GEOCENTRIC_SPHERICAL,
                GEOCENTRIC_SPHERICAL,
                check_validity=False,
            )
            model_data[:, 2] *= -1
            # set the dataset
            f_var, b_var = self.variables
            if f_var in variables:
                output_ds.set(f_var, vnorm(model_data), CDF_DOUBLE_TYPE)
            if b_var in variables:
                output_ds.set(b_var, model_data, CDF_DOUBLE_TYPE)
        return output_ds
