#-------------------------------------------------------------------------------
#
# Variable dependency resolver
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2017-2023 EOX IT Services GmbH
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
# pylint: disable=too-many-instance-attributes

from collections import OrderedDict, defaultdict
from itertools import chain
from vires.util import unique
from vires.filters import Filter, RejectAll
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


class VariableResolver:
    """ Variable Resolver collects the available sources, models and filters
    and resolves the variable consumer/producer dependencies.
    """

    def __init__(self):
        self._producers = OrderedDict()
        self._consumers = defaultdict(set)
        self._unresolved = defaultdict(set)

        self._sources = []
        self._models = []
        self._filters = []
        self._unresolved_filters = []
        self._output_variables = []

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

    def reduce(self):
        """ Reduce dependencies by removing non-consumed producers.

        This is an iterative process as each removed producer can lead
        to a new one. The reduction is repeated until there is no non-consumed
        producer left.

        The reduction algorithm also removes unresolved and unnecessary
        consumers, except the special output consumer (set to None).
        """
        if self._unresolved:
            removed = set()
            for unresolved in self._unresolved.values():
                removed.update(item for item in unresolved if item)
            self._remove_consumers(removed)

        # perform the iterative reduction
        while True:
            removed = self._get_nonconsumed_producters()
            if not removed:
                break
            self._remove_producers(removed)
            self._remove_consumers(removed)

    def add_output_variables(self, variables):
        """ Add requested output variables.

        The output is a special type of consumer (None) with required variables.
        Currently, the unresolved variables are ignored, i.e., the output
        is fed with the resolved variables only.
        """
        if variables is None:
            variables = self._producers
        resolved_variables, _ = self._add_consumer(variables, None)
        self._output_variables = list(unique(chain(
            self._output_variables, resolved_variables
        )))

    def add_master(self, master):
        """ Add the master source time-series.

        The master source does not require any variable and contributes solely
        to the available (provided) variables. Only one master is allowed.
        """
        if self._sources:
            raise RuntimeError("Master is already set!")
        self._add_producer(master.variables, master)
        self._sources.append(master)

    def add_consumer(self, node):
        """ Add generic consumer. """
        if isinstance(node, Model):
            self.add_model(node)
        elif isinstance(node, TimeSeries):
            self.add_slave(node)
        elif isinstance(node, Filter):
            self.add_filter(node)
        else:
            raise ValueError(f"Unexpected consumer type {node!r}")

    def add_slave(self, slave):
        """ Add a new slave source time-series.

        The slave source requires the given matching variable (usually time).
        Any number of slaves is allowed.
        """
        if not self._sources:
            raise RuntimeError("No master is set!")
        _, unresolved_variables = self._add_consumer(
            slave.required_variables, slave
        )
        if not unresolved_variables:
            offered_variables = self._add_producer(slave.variables, slave)
            if offered_variables:
                self._sources.append(slave)

    def add_model(self, model):
        """ Add model.

        A model acts like a function consuming (required) variables and
        transforms them into new (provided) variables.
        """
        _, unresolved_variables = self._add_consumer(
            model.required_variables, model
        )
        if not unresolved_variables:
            offered_variables = self._add_producer(model.variables, model)
            if offered_variables:
                self._models.append(model)

    def add_filter(self, filter_):
        """ Add filter.

        A filter is consuming (required) variables and bases on their values
        extract subset the data samples. A filter does not produce any new
        variables.
        """
        _, unresolved_variables = self._add_consumer(
            filter_.required_variables, filter_
        )
        if unresolved_variables:
            self._unresolved_filters.append(filter_)
        else:
            self._filters.append(filter_)

    def add_filters(self, filters):
        """ Add multiple new filters from a sequence. """
        for filter_ in filters:
            self.add_filter(filter_)

    def _add_producer(self, variables, producer):
        """ Add producer providing the given variables. """
        offered_variables = []
        for variable in variables:
            if variable not in self._producers:
                self._producers[variable] = producer
                offered_variables.append(variable)
        return offered_variables

    def _remove_producers(self, removed):
        """ Remove the given producers from the resolver. """
        for variable, producer in list(self._producers.items()):
            if producer in removed:
                del self._producers[variable]

        for producer in removed:
            if isinstance(producer, Model):
                self._models.remove(producer)
            elif isinstance(producer, TimeSeries):
                idx = self._sources.index(producer)
                if idx > 0: # only slaves can be removed
                    self._sources.pop(idx)

    def _add_consumer(self, required_variables, consumer):
        """ Add consumer requiring the given variables. """
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

    def _remove_consumers(self, removed):
        """ Remove the given consumers from the resolver. """
        for variable, consumers in list(self._consumers.items()):
            consumers.difference_update(removed)
            if not consumers:
                del self._consumers[variable]

    def _get_nonconsumed_producters(self):
        """ Get non-consumed producers. """
        consumed = set()
        nonconsumed = set()
        for variable, producer in self._producers.items():
            if variable in self._consumers:
                consumed.add(producer)
            else:
                nonconsumed.add(producer)
        return nonconsumed - consumed
