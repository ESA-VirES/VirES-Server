#-------------------------------------------------------------------------------
#
# Data Source - magnetic model residual
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
#pylint: disable=too-many-locals,too-many-arguments,too-few-public-methods

from logging import getLogger, LoggerAdapter
from vires.util import cached_property, pretty_list
from vires.dataset import Dataset
from ..base import Model


class MagneticModelResidual(Model):
    """ Residual evaluation.

    Residual is evaluated as a difference between the measurement and
    model value.
    """
    MODEL_VARIABLES = {
        "B_NEC1": "B_NEC",
        "B_NEC2": "B_NEC",
        "B_NEC3": "B_NEC",
    }

    @cached_property
    def variables(self):
        return [f"{self.variable}_res_{self.model_name}"]

    @cached_property
    def required_variables(self):
        return [self.variable, f"{self.model_variable}_{self.model_name}"]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            residual_name = self.extra["residual_name"]
            return f"{residual_name}: {msg}", kwargs

    def __init__(self, model_name, variable, logger=None):
        super().__init__()
        self.model_name = model_name
        self.variable = variable
        self.model_variable = self.MODEL_VARIABLES.get(variable, variable)
        self.logger = self._LoggerAdapter(
            logger or getLogger(__name__),
            {"residual_name": self.variables[0]}
        )

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        output_variable, = self.variables
        is_requested = variables is None or output_variable in variables
        self.logger.debug(
            "requested variables %s",
            pretty_list(self.variables if is_requested else ())
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
            base = "Magnetic field vector residual, NEC frame"
        else:
            base = "Magnetic field intensity residual"

        return {
            "DESCRIPTION": (
                f"{base}, calculated as a difference of the measurement and "
                f"value of the {self.model_name} spherical harmonic model"
            ),
            "UNITS": src_attr["UNITS"]
        }
