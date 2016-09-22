#-------------------------------------------------------------------------------
#
#  Dataset Class
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

from collections import OrderedDict
from numpy import array, concatenate
from vires.util import include
from .interpolate import Interp1D


class Dataset(OrderedDict):
    """ Dataset class.  Basically an ordered dictionary with a few additional
    properties and methods.
    """

    def __init__(self, *args, **kwds):
        OrderedDict.__init__(self, *args, **kwds)
        self.cdf_type = {}
        if args and hasattr(args[0], 'cdf_type'):
            self.cdf_type.update(args[0].cdf_type)

    @property
    def length(self):
        """ Get length of the dataset (length of the arrays held by the
        dataset).
        """
        return self.itervalues().next().shape[0] if len(self) else 0

    def set(self, variable, data, cdf_type=None):
        """ Set variable. """
        data = array(data, copy=False)
        if len(self):
            if self.itervalues().next().shape[0] != data.shape[0]:
                raise ValueError("Array size mismatch!")
        self[variable] = data
        if cdf_type is not None:
            self.cdf_type[variable] = cdf_type

    def merge(self, dataset):
        """ Merge a dataset to this one. Unlike the update method the merge
        does not replace the existing variables and only the new variables
        are added to this dataset.
        """
        for variable, data in dataset.iteritems():
            if variable not in self:
                self.set(variable, data, dataset.cdf_type.get(variable))

    def append(self, dataset):
        """ Append dataset of the same kind to this dataset. All variables
        are concatenated with the current dataset data.
        """
        if dataset: # ignore empty datasets
            if self: # concatenate with the current data
                self.update(
                    (variable, concatenate((data, dataset[variable]), axis=0))
                    for variable, data in self.iteritems()
                )
            else: # fill empty dataset
                for variable, data in dataset.iteritems():
                    self.set(variable, data, dataset.cdf_type.get(variable))

    def subset(self, index, always_copy=True):
        """ Get subset of the dataset defined by the array of indices. """
        if index is None: # no-index means select all
            dataset = Dataset(self) if always_copy else self
        else:
            dataset = Dataset(
                ((var, data[index]) for var, data in self.iteritems()),
            )
            dataset.cdf_type.update(self.cdf_type)
        return dataset

    def extract(self, variables):
        """ Get new subset containing only the selected variables. """
        dataset = Dataset()
        for variable in variables:
            if variable in self:
                dataset.set(
                    variable, self[variable], self.cdf_type.get(variable)
                )
        return dataset

    def interpolate(self, values, variable, variables=None, kinds=None):
        """ 1D time-series interpolation at 'values' of the given 'variable'.
        The 'kinds' of interpolation can be specified by the user defined
        dictionary. The supported kinds are: last, nearest, linear.
        """
        dataset = Dataset()

        if self.length < 2: # dataset is too short to be interpolated
            # TODO: implement NaN fill
            return dataset

        interp1d = Interp1D(self[variable], values)
        variables = (
            self if variables is None else include(variables, self)
        )

        for variable in variables:
            kind = (kinds or {}).get(variable, 'nearest')
            data = self[variable]
            dataset.set(
                variable, interp1d(data, kind).astype(data.dtype),
                self.cdf_type.get(variable) # TODO: change the CDF type to float
            )

        return dataset
