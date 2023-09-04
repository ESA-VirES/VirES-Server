#-------------------------------------------------------------------------------
#
# Model expression and list parser
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
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

from itertools import chain
from collections import namedtuple
from numpy import inf
from eoxmagmod import ComposedGeomagneticModel
from vires.util import cached_property


class ComposedMagneticModel:
    """ Composed magnetic model. """

    Component = namedtuple("Component", ["scale", "model"])

    @cached_property
    def expression(self):
        """ Composed model expression """
        def _generate_parts():
            components = iter(self.components)
            try:
                scale, model = next(components)
            except StopIteration:
                return
            sign = "- " if scale < 0 else ""
            yield f"{sign}{model.expression}"
            for scale, model in components:
                sign = "-" if scale < 0 else "+"
                yield f"{sign} {model.expression}"

        return " ".join(_generate_parts())

    @cached_property
    def validity(self):
        """ Get model validity period. """
        if not self.components: # an empty composed model
            return -inf, -inf

        start, end = -inf, +inf
        for _, model in self.components:
            comp_start, comp_end = model.validity
            start = max(start, comp_start)
            end = min(end, comp_end)
            if start > end: # no validity overlap
                return -inf, -inf

        return start, end

    @cached_property
    def model(self):
        """ Get aggregated model. """
        aggregated_model = ComposedGeomagneticModel()
        for component in self.components:
            aggregated_model.push(
                model=component.model.model,
                scale=component.scale,
                **component.model.parameters,
            )
        return aggregated_model

    @cached_property
    def sources(self):
        """ Get model sources and their validity ranges. """
        return list(chain.from_iterable(
            component.model.sources for component in self.components
        ))

    @cached_property
    def name(self):
        """ Get model name. """
        return self.identifier

    def __init__(self, identifier, components):
        self.identifier = identifier
        self.components = components

    def __str__(self):
        return f"<ComposedMagneticModel: {self.identifier} = {self.expression}>"
