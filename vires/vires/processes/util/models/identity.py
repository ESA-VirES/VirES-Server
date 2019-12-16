#-------------------------------------------------------------------------------
#
# Variable Identity - special "model" class creating a copy of a variable.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
from vires.dataset import Dataset
from .base import Model


class Identity(Model):
    """ Special simple model copying a variable and publishing it under
    a new name.
    """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'Identity: %s' % msg, kwargs

    def __init__(self, variable_source, variable_target, logger=None):
        super(Identity, self).__init__()
        self._source = variable_source
        self._target = variable_target
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    @property
    def required_variables(self):
        return [self._source]

    @property
    def variables(self):
        return [self._target]

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = (
            self.variables if variables is None or self._target in variables
            else []
        )
        if variables:
            self.logger.debug("copying %s to %s", self._source, self._target)
            output_ds.set(
                self._target, dataset[self._source],
                dataset.cdf_type.get(self._source),
                dataset.cdf_attr.get(self._source),
            )
        return output_ds
