#-------------------------------------------------------------------------------
#
# Variable dependency resolver
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
# pylint: disable=too-many-arguments, too-many-locals, too-many-branches
# pylint: disable=too-many-instance-attributes, missing-docstring

from collections import OrderedDict, defaultdict
from itertools import chain
from vires.util import unique
from .filters import RejectAll
from .time_series import TimeSeries
from .models import Model


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
    and resolves the variable consumer/producer dependencies.
    """

    def nonconsumed_producters(self):
        """ Get non-consumed producers. """
        consumed = set()
        nonconsumed = set()
        for variable, producer in self._producers.items():
            if variable in self._consumers:
                consumed.add(producer)
            else:
                nonconsumed.add(producer)
        return nonconsumed - consumed

    def remove_producers(self, removed):
        """ Remove consumers. """
        for variable, producer in self._producers.items():
            if producer in removed:
                del self._producers[variable]

        for producer in removed:
            if isinstance(producer, Model):
                self._models.remove(producer)
            elif isinstance(producer, TimeSeries):
                idx = self._sources.index(producer)
                if idx > 0: # only slaves can be removed
                    self._sources.pop(idx)

    def remove_consumers(self, removed):
        """ Remove consumers. """
        for variable, consumers in self._consumers.items():
            consumers.difference_update(removed)
            if not consumers:
                del self._consumers[variable]

    def reduce(self):
        """ Reduce dependencies by removing non-consumed producers. """
        while True:
            removed = self.nonconsumed_producters()
            if not removed:
                break
            self.remove_producers(removed)
            self.remove_consumers(removed)

    def __init__(self):
        self._producers = OrderedDict()
        self._consumers = defaultdict(set)
        self._unresolved = defaultdict(set)

        self._sources = []
        self._models = []
        self._filters = []
        self._unresolved_filters = []
        self._output_variables = []

    def _add_producer(self, variables, producer):
        offered_variables = []
        for variable in variables:
            if variable not in self._producers:
                self._producers[variable] = producer
                offered_variables.append(variable)
        return offered_variables

    def _add_consumer(self, required_variables, consumer):
        resolved_variables = []
        unresolved_variables = []
        for variable in required_variables:
            if variable in self._producers:
                self._consumers[variable].add(consumer)
                resolved_variables.append(variable)
            else:
                self._unresolved[variable].add(consumer)
                unresolved_variables.append(variable)
        return resolved_variables, unresolved_variables

    def add_output_variables(self, variables):
        """ Add required output variables. """
        if variables is None:
            variables = self._producers
        resolved_variables, _ = self._add_consumer(variables, None)
        self._output_variables = list(unique(chain(
            self._output_variables, resolved_variables
        )))

    def add_master(self, master):
        """ Add the master source. Only one master allowed.
        The master source does not require any variables and contribute solely
        to the available available variables.
        """
        if self._sources:
            raise RuntimeError("Master is already set!")
        self._add_producer(master.variables, master)
        self._sources.append(master)

    def add_slave(self, slave, matching_variable):
        """ Add a new slave source. Any number of slaves is allowed.
        The slave source requires only the matching variables to be available.
        """
        if not self._sources:
            raise RuntimeError("No master is set!")
        _, unresolved_variables = self._add_consumer([matching_variable], slave)
        if not unresolved_variables:
            offered_variables = self._add_producer(slave.variables, slave)
            if offered_variables:
                self._sources.append(slave)

    def add_model(self, model):
        """ Add model """
        _, unresolved_variables = self._add_consumer(
            model.required_variables, model
        )
        if not unresolved_variables:
            offered_variables = self._add_producer(model.variables, model)
            if offered_variables:
                self._models.append(model)

    def add_filter(self, filter_):
        """ Add filter """
        _, unresolved_variables = self._add_consumer(
            filter_.required_variables, filter_
        )
        if unresolved_variables:
            self._unresolved_filters.append(filter_)
        else:
            self._filters.append(filter_)

    def add_filters(self, filters):
        """ Add new filters from a sequence. """
        for filter_ in filters:
            self.add_filter(filter_)

    @property
    def output_variables(self):
        """ List of output variables. """
        return list(self._output_variables)

    @property
    def available(self):
        """ List of all available variables. """
        return list(self._producers)

    @property
    def required(self):
        """ List of all required variables. """
        return list(self._consumers)

    @property
    def unresolved(self):
        """ List of all unresolved variables. """
        return list(self._unresolved)

    @property
    def time_series(self):
        """ Get list of source time series."""
        return list(self._sources)

    @property
    def master(self):
        """ Get master time-series. """
        return self._sources[0] if self._sources else None

    @property
    def slaves(self):
        """ Get list of slaves time-series."""
        return list(self._sources[1:])

    @property
    def models(self):
        """ Get list of all models."""
        return list(self._models)

    @property
    def filters(self):
        """ Get list of applicable resolved filters. """
        if self._unresolved_filters:
            return [RejectAll()]
        return list(self._filters)

    @property
    def unresolved_filters(self):
        """ Get list of unresolved filters. """
        return list(self._unresolved_filters)
