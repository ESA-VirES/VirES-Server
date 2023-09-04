#-------------------------------------------------------------------------------
#
# Vector Intensity - models calculating scalar intensities of input vectors
#                    e.g., F from B_NEC
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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
#pylint: disable=too-many-arguments,missing-docstring

from logging import getLogger, LoggerAdapter
from eoxmagmod import vnorm
from vires.util import pretty_list
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class VectorIntensity(Model):
    """ Calculate intensity of a vector field. """
    CDF_TYPE = CDF_DOUBLE_TYPE

    class _LoggerAdapter(LoggerAdapter):

        def __init__(self, logger, extra, source, target):
            super(VectorIntensity._LoggerAdapter, self).__init__(logger, extra)
            self._label = f"VectorIntensity[{source}=>{target}]"

        def process(self, msg, kwargs):
            return f"{self._label}: {msg}", kwargs

    @property
    def variables(self):
        return [self._target_variable]

    @property
    def required_variables(self):
        return [self._source_variable]

    def __init__(self, source, target, attrs=None, logger=None, varmap=None):
        super().__init__()
        self._source_variable = (varmap or {}).get(source, source)
        self._target_variable = target
        self._attrs = attrs or {}
        self.logger = self._LoggerAdapter(
            logger or getLogger(__name__), {},
            self._source_variable, self._target_variable,
        )

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = (self.variables if (
            variables is None or self._target_variable in variables
        ) else [])
        self.logger.debug("requested variables: %s", pretty_list(variables))
        if variables:
            data = vnorm(dataset[self._source_variable])
            output_ds.set(self._target_variable, data, CDF_DOUBLE_TYPE, self._attrs)
        return output_ds


class BnecToF(VectorIntensity):
    """ Calculate intensity of the B_NEC vector. """

    def __init__(self, *args, **kwargs):
        super().__init__("B_NEC", "F", {
            'DESCRIPTION': 'Total magnetic field strength',
            'UNITS': 'nT',
        }, *args, **kwargs)
