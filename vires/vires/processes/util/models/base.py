#-------------------------------------------------------------------------------
#
# Model base class - computed data sources
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
# pylint: disable=missing-docstring

class Model(object):
    """ Base model source class. """

    def __init__(self):
        self.product_set = set() # stores all recorded source products

    @property
    def products(self):
        """ Get list of all accessed products. """
        return list(self.product_set)

    @property
    def variables(self):
        """ Get list of the provided variables. """
        raise NotImplementedError

    @property
    def required_variables(self):
        """ Get list of the required input dataset variables. """
        raise NotImplementedError

    def eval(self, dataset, variables=None, **kwargs):
        """ Evaluate model for the given dataset.
        Optionally the content of the output dataset can be controlled
        by the list of the output variables.
        Specific models can define additional keyword parameters.
        """
        raise NotImplementedError
