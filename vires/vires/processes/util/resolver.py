#-------------------------------------------------------------------------------
#
# Variable Dependency Resolver
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=too-many-arguments, too-many-locals, too-many-branches
# pylint: disable=too-many-instance-attributes

from itertools import chain
from vires.util import unique, include, exclude
from .filters import RejectAll


def extract_product_names(resolvers):
    """ Extract product names from the resolvers time-series and models. """
    def _extract_product_sets(resolver):
        for item in resolver.models:
            yield item.product_set
        for item in resolver.time_series:
            yield item.product_set

    product_set = set()
    for resolver in resolvers:
        for item in _extract_product_sets(resolver):
            product_set.update(item)

    return list(sorted(product_set))


class VariableResolver(object):
    """ Variable Resolver collects the available sources, models and filters
    and resolves the variable dependencies.

    Variables types:
        output:    list of all output variables.
        available: list of all available variables which can be used
                   in the output.
        requested: optional list of variables requested by the user
                   to be in the output. If not set all available variables
                   are used.
        mandatory: optional list of variables desired always in the output
                   even if not explicitly requested.
        required:  variables which are required to be available in order
                   to evaluate the outputs
    """

    def __init__(self, requested=None, mandatory=None, required=None):
        self.requested = tuple(unique(requested)) if requested else ()
        self.mandatory = tuple(unique(mandatory)) if mandatory else ()
        self._available_list = []
        self._available_set = set()
        self._required_set = set(required if required else ())

        self.master = None
        self.slaves = []
        self.models = []
        self._resolved_filters = []
        self._unresolved_filters = []

    @property
    def time_series(self):
        """ Get list of all time series. """
        time_series = []
        if self.master:
            time_series.append(self.master)
        time_series.extend(self.slaves)
        return time_series

    @property
    def available(self):
        """ Get tuple of available variables. """
        return tuple(unique(self._available_list))

    @property
    def output(self):
        """ Get tuple of output variables. """
        available = self.available
        output = (
            include(self.requested, available) if self.requested else available
        )
        return tuple(chain(
            include(self.mandatory, available), # mandatory first
            exclude(output, self.mandatory)
        ))

    @property
    def required(self):
        """ Get tuple of variables required to be evaluated. """
        return tuple(unique(chain(self.output, self._required_set)))

    @property
    def unresolved_filters(self):
        """ Get list of unresolved filters. """
        return tuple(self._unresolved_filters)

    @property
    def resolved_filters(self):
        """ Get list of applicable resolved filters. """
        return tuple(self._resolved_filters)

    @property
    def filters(self):
        """ Get list of filters to be applied to the data."""
        if self._unresolved_filters:
            return (RejectAll(),)
        return self.resolved_filters

    def add_master(self, master):
        """ Add the master source. Only one master allowed.
        The master source does not require any variables and contribute solely
        to the available available variables.
        """
        if self.master:
            raise RuntimeError("Master is already set!")
        self._available_set.update(master.variables)
        self._available_list.extend(master.variables)
        self.master = master

    def add_slave(self, slave, matching_variable):
        """ Add a new slave source. Any number of slaves is allowed.
        The slave source requires only the matching variables to be available.
        """
        if matching_variable in self._available_set:
            self._required_set.add(matching_variable)
            self._available_list.extend(slave.variables)
            self._available_set.update(slave.variables)
            self.slaves.append(slave)

    def add_model(self, model):
        """ Add derived model variables.
        The derived variables require certain variables to be present
        in order to be evaluated.
        """
        if not set(model.required_variables) - self._available_set:
            self._required_set.update(model.required_variables)
            self._available_list.extend(model.variables)
            self._available_set.update(model.variables)
            self.models.append(model)

    def add_filter(self, filter_):
        """ Add new filter and check whether its dependencies are satisfied.
        """
        if not set(filter_.required_variables) - self._available_set:
            self._required_set.update(filter_.required_variables)
            self._resolved_filters.append(filter_)
        else:
            self._unresolved_filters.append(filter_)

    def add_filters(self, filters):
        """ Add new filters from a sequence. """
        for filter_ in filters:
            self.add_filter(filter_)
