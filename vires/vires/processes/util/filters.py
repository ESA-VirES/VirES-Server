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
from vires.util import between

def apply_filters(dataset, filters, filters_applied=None, index=None):
    """ Apply list of filters to a dataset.
    The function returns a new dataset subset, list of applied filters,
    and list of filters not applied due to the missing required dataset
    variables.
    """
    applied = [] if filters_applied is None else list(filters_applied)
    remaining = []
    varset = set(dataset)
    for filter_ in filters:
        if varset.issuperset(filter_.required_variables):
            index = filter_.filter(dataset, index)
            applied.append(filter_)
        else:
            remaining.append(filter_)
    return dataset.subset(index), applied, remaining


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
        return [self.variable]

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
        if index is None:
            index = self._filter(data).nonzero()[0]
        if index is None:
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
        if index is None:
            index = self._filter(data[:, self.component]).nonzero()[0]
        if index is None:
            index = index[self._filter(data[index, self.component])]
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

    def __str__(self):
        ";".join(str(filter_) for filter_ in self.filters)
