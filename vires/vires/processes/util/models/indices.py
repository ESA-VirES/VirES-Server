#-------------------------------------------------------------------------------
#
# Data Source - Kp10 to Kp index conversion.
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
#pylint: disable=missing-docstring

from logging import getLogger, LoggerAdapter
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class IndexKpFromKp10(Model):
    """ Conversion of Kp10 to Kp.
    """
    REQUIRED_VARIABLE = "Kp10"
    PROVIDED_VARIABLE = "Kp"
    CDF_VARIABLE = (
        CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Global geo-magnetic storm index.',
            'UNITS': '-',
        }
    )

    @property
    def variables(self):
        return [self.PROVIDED_VARIABLE]

    @property
    def required_variables(self):
        return [self._required_variable]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'KpFromKp10: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super(IndexKpFromKp10, self).__init__()
        varmap = varmap or {}
        self._required_variable = varmap.get(
            self.REQUIRED_VARIABLE, self.REQUIRED_VARIABLE
        )
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        required_variable = self._required_variable
        provided_variable = self.PROVIDED_VARIABLE

        eval_kp = variables is None or provided_variable in variables

        self.logger.debug(
            "requested variables: %s", required_variable if eval_kp else ""
        )

        if eval_kp:
            output_ds.set(
                provided_variable, 0.1*dataset[required_variable],
                *self.CDF_VARIABLE
            )

        return output_ds
