#-------------------------------------------------------------------------------
#
#  Data filters.
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

from logging import getLogger, LoggerAdapter
from numpy import arange
from vires.util import between


class Filter(object):
    """ Base filter class. """

    @property
    def required_variables(self):
        """ Get a list of the dataset variables required by this filter.
        """
        raise NotImplementedError

    def filter(self, dataset, index=None):
        """ Filter dataset. Optionally a dataset subset index can be provided.
        A new array of indices identifying the filtered data subset is returned.
        """
        raise NotImplementedError


class ScalarRangeFilter(Filter):
    """ Simple scalar value range filter. """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'filter %s: %s' % (self.extra["variable"], msg), kwargs

    def __init__(self, variable, vmin, vmax, logger=None):
        self.variable = variable
        self.vmin = vmin
        self.vmax = vmax
        self.logger = self._LoggerAdapter(
            logger or getLogger(__name__), {"variable": self.variable}
        )

    @property
    def required_variables(self):
        return [self.variable]

    def filter(self, dataset, index=None):
        self.logger.debug("value range: %s %s", self.vmin, self.vmax)
        return self._filter(dataset[self.variable], index)

    def _filter(self, data, index):
        """ Low-level range filter. """
        if index is None:
            self.logger.debug("initial size: %d", data.size)
            index = between(data, self.vmin, self.vmax).nonzero()[0]
        else:
            self.logger.debug("initial size: %d", index.size)
            index = index[between(data[index], self.vmin, self.vmax)]
        self.logger.debug("filtered size: %d", index.size)
        return index


class BoundingBoxFilter(Filter):
    """ Bounding box filter. """

    def __init__(self, variables, bbox):
        self._variables = variables
        self.filters = [
            ScalarRangeFilter(variable, vmin, vmax)
            for variable, (vmin, vmax) in zip(variables, zip(bbox[0], bbox[1]))
        ]

    @property
    def required_variables(self):
        return self._variables

    def filter(self, dataset, index=None):
        for filter_ in self.filters:
            index = filter_.filter(dataset, index)
        return index
