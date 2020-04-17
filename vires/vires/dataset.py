#-------------------------------------------------------------------------------
#
#  Dataset Class - data container
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
# pylint: disable=too-many-arguments

from collections import OrderedDict
from numpy import array, concatenate, inf
from .util import include, unique
from .cdf_util import CDF_DOUBLE_TYPE
from .interpolate import Interp1D


class Dataset(OrderedDict):
    """ Dataset class an ordered dictionary of arrays with a few additional
    properties and methods.
    """
    def __init__(self, dataset=None):
        OrderedDict.__init__(self)
        self.cdf_type = {}
        self.cdf_attr = {}
        if dataset is not None:
            self.update(dataset)

    @property
    def length(self):
        """ Get length of the dataset (length of the arrays held by the
        dataset).
        """
        return next(iter(self.values())).shape[0] if self else 0

    def set(self, variable, data, cdf_type=None, cdf_attr=None):
        """ Set variable. """
        data = array(data, copy=False)
        if self and self.length != data.shape[0]:
            raise ValueError(
                "Array size mismatch! variable: %s, size: %s, dataset: %s" %
                (variable, data.shape[0], self.length)
            )
        self[variable] = data
        if cdf_type is not None:
            self.cdf_type[variable] = cdf_type
        if cdf_attr is not None:
            self.cdf_attr[variable] = dict(cdf_attr)

    def merge(self, dataset):
        """ Merge datasets.
        The merge adds variables from the given dataset if these are not already
        present otherwise the variables are ignored.
        """
        if self and dataset and self.length != dataset.length:
            raise ValueError(
                "Dataset length mismatch! %s != %s" %
                (dataset.length, self.length)
            )

        for variable, data in dataset.items():
            if variable not in self:
                self.set(
                    variable, data,
                    dataset.cdf_type.get(variable),
                    dataset.cdf_attr.get(variable)
                )

    def update(self, dataset):
        """ Update the given dataset with this one.
        The merge adds variables from the given dataset replacing variables
        already present in the dataset.
        """
        if self and dataset and self.length != dataset.length:
            raise ValueError(
                "Dataset length mismatch! %s != %s" %
                (dataset.length, self.length)
            )

        for variable, data in dataset.items():
            self.set(
                variable, data,
                dataset.cdf_type.get(variable),
                dataset.cdf_attr.get(variable)
            )

    def append(self, dataset):
        """ Append dataset of the same kind to this dataset. All variables
        are concatenated with the current dataset data.
        """
        if dataset: # ignore empty datasets
            if not self:
                # fill empty dataset
                self.update(dataset)
            else:
                if set(dataset) != set(self):
                    raise ValueError("Dataset variables mismatch! %s != %s " % (
                        list(set(dataset) - set(self)),
                        list(set(self) - set(dataset))
                    ))
                # concatenate with the current data
                OrderedDict.update(self, (
                    (variable, concatenate((data, dataset[variable]), axis=0))
                    for variable, data in self.items()
                ))

    def subset(self, index, always_copy=True):
        """ Get subset of the dataset defined by the array of indices. """
        if index is None: # no-index means select all
            dataset = Dataset(self) if always_copy else self
        elif self.length == 0 and index.size == 0:
            # Older Numpy versions fail to apply zero subset of a zero size
            # multi-dimensional array.
            dataset = Dataset(self)
        else:
            dataset = Dataset()
            for variable, data in self.items():
                dataset.set(
                    variable, data[index],
                    self.cdf_type.get(variable),
                    self.cdf_attr.get(variable)
                )
        return dataset

    def extract(self, variables):
        """ Get new subset containing only the selected variables. """
        dataset = Dataset()
        for variable in set(variables):
            try:
                data = self[variable]
            except KeyError:
                pass # non-existent variables are silently ignored
            else:
                dataset.set(
                    variable, data,
                    self.cdf_type.get(variable),
                    self.cdf_attr.get(variable)
                )
        return dataset

    def interpolate(self, values, variable, variables=None, kinds=None,
                    gap_threshold=inf, segment_neighbourhood=0):
        """ 1D time-series interpolation at 'values' of the given 'variable'.
        The 'kinds' of interpolation can be specified by the user defined
        dictionary. The supported kinds are: last, nearest, linear.
        The values as well the variable must be sorted in ascending order.
        """
        if kinds is None:
            kinds = {}
        dataset = Dataset()

        interp1d = Interp1D(
            self[variable], values, gap_threshold, segment_neighbourhood
        )
        variables = (
            self if variables is None else include(unique(variables), self)
        )

        for name in variables:
            kind = kinds.get(name, 'nearest')
            data = self[name]
            dataset.set(
                name, interp1d(data, kind).astype(data.dtype),
                CDF_DOUBLE_TYPE, #self.cdf_type.get(name),
                self.cdf_attr.get(name)
            )

        return dataset

    def filter(self, filters, index=None, always_copy=False):
        """ Filter dataset by the given list of filters.
        The function returns a new dataset subset and list of filters
        not applied due to the missing required dataset variables.
        In case of no filter the same unchanged dataset is returned.
        """
        remaining = []
        varset = set(self)
        for filter_ in filters:
            if varset.issuperset(filter_.required_variables):
                index = filter_.filter(self, index)
            else:
                remaining.append(filter_)
        return self.subset(index, always_copy), remaining

    def __str__(self):
        def _generate_():
            yield "Dataset:"
            for key in self:
                data = self[key]
                yield "%s: shape: %s" % (key, data.shape)
                yield "%s: dtype: %s" % (key, data.dtype)
                yield "%s: cdf_type: %s" % (key, self.cdf_type.get(key))
                yield "%s: cdf_attr: %s" % (key, self.cdf_attr.get(key, {}))
                yield "%s: data:\n%s" % (key, data)
        return "\n".join(_generate_())
