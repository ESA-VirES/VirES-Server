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
# pylint: disable=too-many-arguments

from logging import getLogger, LoggerAdapter
from numpy import array, concatenate, unique
from vires.util import between


def merge_indices(*indices):
    """ Merge indices eliminating duplicate values. """
    indices = [index for index in indices if index is not None]
    if len(indices) > 1:
        return unique(concatenate(indices))
    elif len(indices) == 1:
        return indices[0]
    return array([], dtype='int64')


class FilterError(Exception):
    """ Base filter error exception. """


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

    def __str__(self):
        raise NotImplementedError


class RejectAll(Filter):
    """ Filter rejecting all records. """

    @property
    def required_variables(self):
        return ()

    def filter(self, dataset, index=None):
        return array([], dtype='int64')

    def __str__(self):
        return "RejectAll()"


class BaseRangeFilter(Filter):
    """ Base scalar value range filter. """
    # pylint: disable=abstract-method

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'filter %s: %s' % (self.extra["variable"], msg), kwargs

    def __init__(self, variable, vmin, vmax, logger):
        self.variable = variable
        self.vmin = vmin
        self.vmax = vmax
        self.logger = logger

    @property
    def label(self):
        """ Get filter label. """
        return self.variable

    @property
    def required_variables(self):
        return (self.variable,)

    def _filter(self, data):
        """ Low level filter. """
        self.logger.debug("value range: %s %s", self.vmin, self.vmax)
        self.logger.debug("initial size: %d", data.shape[0])
        return between(data, self.vmin, self.vmax)

    def __str__(self):
        return "%s:%.17g,%.17g" % (self.label, self.vmin, self.vmax)


class ScalarRangeFilter(BaseRangeFilter):
    """ Simple scalar value range filter. """

    def __init__(self, variable, vmin, vmax, logger=None):
        BaseRangeFilter.__init__(
            self, variable, vmin, vmax, self._LoggerAdapter(
                logger or getLogger(__name__), {"variable": variable}
            )
        )

    def filter(self, dataset, index=None):
        data = dataset[self.variable]
        if data.ndim != 1:
            raise FilterError(
                "An attempt to apply a scalar range filter to a non-scalar "
                "variable %s!" % self.variable
            )
        if index is None:
            index = self._filter(data).nonzero()[0]
        else:
            index = index[self._filter(data[index])]
        self.logger.debug("filtered size: %d", index.size)
        return index


class VectorComponentRangeFilter(BaseRangeFilter):
    """ Single vector component range filter. """

    def __init__(self, variable, component, vmin, vmax, logger=None):
        BaseRangeFilter.__init__(
            self, variable, vmin, vmax, self._LoggerAdapter(
                logger or getLogger(__name__), {
                    "variable": "%s[%s]" % (variable, component)
                }
            )
        )
        self.component = component

    @property
    def label(self):
        return "%s[%d]" % (self.variable, self.component)

    def filter(self, dataset, index=None):
        data = dataset[self.variable]
        if data.ndim != 2:
            raise FilterError(
                "An attempt to apply a vector component range filter to a "
                "non-vector variable %s!" % self.variable
            )
        if index is None:
            index = self._filter(data[:, self.component]).nonzero()[0]
        else:
            index = index[self._filter(data[index, self.component])]
        self.logger.debug("filtered size: %d", index.size)
        return index


class BoundingBoxFilter(Filter):
    """ Bounding box filter. """

    def __init__(self, variables, bbox):
        self._variables = tuple(variables)
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

    def __str__(self):
        return ";".join(str(filter_) for filter_ in self.filters)
