#-------------------------------------------------------------------------------
#
# Data Source - magnetic models and model residuals
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
#pylint: disable=too-many-locals,too-many-arguments,too-few-public-methods

from logging import getLogger, LoggerAdapter
from itertools import chain
from numpy import zeros
from eoxmagmod import vnorm
from vires.util import include, unique, cached_property, pretty_list
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from ..base import Model


class ComposedMagneticModel(Model):
    """ Combined forward spherical harmonic expansion model. """
    BASE_VARIABLES = ["F", "B_NEC"]

    @cached_property
    def variables(self):
        return [f"{variable}_{self.name}" for variable in self.BASE_VARIABLES]

    @cached_property
    def required_variables(self):
        return [
            f"B_NEC_{component.model.name}"
            for component in self.composed_model.components
        ]

    @cached_property
    def name(self):
        """ composed model name """
        return self.composed_model.name

    @cached_property
    def expression(self):
        """ Composed model expression. """
        return self.composed_model.expression

    @property
    def validity(self):
        """ Get model validity period. """
        return self.composed_model.validity

    @property
    def model(self):
        """ Get the low-level magnetic model. """
        return self.composed_model.model

    @property
    def sources(self):
        """ Get list of composed model's sources. """
        return sorted(set(chain.from_iterable(
            item.names for item in self.composed_model.sources
        )))

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            model_name = self.extra["model_name"]
            return f"{model_name}: {msg}", kwargs

    def __init__(self, composed_model, logger=None):
        super().__init__()

        # an instance of parsed vires.magnetic_models.parser.ComposedMagneticModel
        self.composed_model = composed_model

        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": self.variables[0],
        })

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables: %s", pretty_list(variables))
        output_ds = Dataset()

        if not variables:
            return output_ds

        b_nec = zeros((dataset.length, 3))
        factors = (
            component.scale for component in self.composed_model.components
        )
        for variable, factor in zip(self.required_variables, factors):
            values = dataset[variable]
            if factor != 1:
                values = factor * values
            b_nec += values

        for variable in variables:
            filter_, type_, attrib = self._output[variable]
            output_ds.set(variable, filter_(b_nec), type_, attrib)

        return output_ds

    @cached_property
    def _output(self):
        f_var, b_var = self.variables
        return {
            f_var: (vnorm, CDF_DOUBLE_TYPE, {
                "DESCRIPTION": (
                    "Magnetic field intensity, calculated by "
                    f"the {self.name} spherical harmonic model"
                ),
                "UNITS": "nT",
            }),
            b_var: (lambda r: r, CDF_DOUBLE_TYPE, {
                "DESCRIPTION": (
                    "Magnetic field vector, NEC frame, calculated by "
                    f"the {self.name} spherical harmonic model"
                ),
                "UNITS": "nT",
            }),
        }
