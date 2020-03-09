#-------------------------------------------------------------------------------
#
# Dataset Label - special model class adding label to all dataset records.
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
#pylint: disable=too-many-arguments,unused-argument

from logging import getLogger, LoggerAdapter
from numpy import full
from vires.cdf_util import CDF_CHAR_TYPE
from vires.dataset import Dataset
from .base import Model


class Label(Model):
    """ Simple no input model-like class adding constant label to all dataset
    records.
    """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'Label: %s' % msg, kwargs

    def __init__(self, variable, label, string_size=1,
                 description=None, unit=None,
                 logger=None, varmap=None):
        super().__init__()
        self._variable = variable
        self._label = str(label)[:string_size]
        self._description = description or ""
        self._unit = unit or "-"
        self._dtype = "|S%d" % string_size
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    @property
    def required_variables(self):
        return []

    @property
    def variables(self):
        return [self._variable]

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = (
            self.variables if variables is None or self._variable in variables
            else []
        )
        self.logger.debug("requested variables %s", variables)
        if variables:
            labels = full(dataset.length, self._label, self._dtype)
            output_ds.set(self._variable, labels, CDF_CHAR_TYPE, {
                'DESCRIPTION': self._description,
                'UNITS': self._unit,
            })
            self.logger.debug("%s: %s", self._variable, self._label)
        return output_ds


class SpacecraftLabel(Label):
    """ Add spacecraft label. """
    VARIABLE = "Spacecraft"
    DESCRIPTION = (
        "Spacecraft identifier (values: 'A', 'B', 'C' or '-' if not available)."
    )

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'SpacecraftLabel: %s' % msg, kwargs

    def __init__(self, label, logger=None, varmap=None):
        Label.__init__(
            self, self.VARIABLE, label, 1, description=self.DESCRIPTION,
            unit="-", logger=logger, varmap=varmap
        )
