#-------------------------------------------------------------------------------
#
# Data Source - magnetic model - MIO model multiplication
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from ..base import Model


class MagneticModelMioMultiplication(Model):
    """ Multiply the bare SH part of the MIO model by the F10.7-based
    multiplication factor.
    """
    VARIABLE_F107 = "F107"
    CDF_TYPE = CDF_DOUBLE_TYPE
    DESCRIPTION = {
        "F": (
            "Magnetic field intensity, calculated by "
            "the {model_name} spherical harmonic model"
        ),
        "B_NEC": (
            "Magnetic field vector, NEC frame, calculated by "
            "the {model_name} spherical harmonic model"
        ),
    }

    @cached_property
    def _attributes(self):
        return {
            "DESCRIPTION": (
                self.DESCRIPTION[self._variable].format(model_name=self.name)
            ),
            "UNITS": "nT",
        }

    @cached_property
    def variables(self):
        return [self._target_variable]

    @cached_property
    def required_variables(self):
        return [self._source_variable, self.VARIABLE_F107]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            model_name = self.extra["model_name"]
            return f"{model_name}: {msg}", kwargs

    def __init__(self, variable, model_name, source_model_name, wolf_ratio,
                 logger=None):
        super().__init__()
        self.name = model_name
        self._variable = variable
        self._target_variable = f"{variable}_{model_name}"
        self._source_variable = f"{variable}_{source_model_name}"
        self.wolf_ratio = wolf_ratio
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": self._target_variable,
        })

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        is_requested = variables is None or self._target_variable in variables
        self.logger.debug(
            "requested variables %s",
            pretty_list(self.variables if is_requested else ())
        )
        if is_requested:
            self.logger.debug("requested dataset length %s", dataset.length)
            raw_mio_model = dataset[self._source_variable]
            factor_shape = (
                raw_mio_model.shape[0], *((1,) * (raw_mio_model.ndim - 1))
            )
            factor = 1.0 + self.wolf_ratio * dataset[self.VARIABLE_F107]
            output_ds.set(
                self._target_variable,
                factor.reshape(factor_shape) * raw_mio_model,
                self.CDF_TYPE,
                self._attributes,
            )
        return output_ds
