#-------------------------------------------------------------------------------
#
# Data Source - magnetic models and model residuals
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
#pylint: disable=too-many-locals,too-many-arguments,too-few-public-methods

from logging import getLogger, LoggerAdapter
from itertools import chain
from numpy import inf, zeros
from eoxmagmod import vnorm, ComposedGeomagneticModel
from vires.util import include, unique, cached_property
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from ..base import Model
from .source_extraction import ExtractSourcesMixIn
from .source_model import SourceMagneticModel


class ComposedMagneticModel(Model, ExtractSourcesMixIn):
    """ Combined forward spherical harmonic expansion model. """
    BASE_VARIABLES = ["F", "B_NEC"]

    @cached_property
    def variables(self):
        return [f"{variable}_{self.name}" for variable in self.BASE_VARIABLES]

    @cached_property
    def required_variables(self):
        return [f"B_NEC_{model.name}" for _, model in self.components]

    @cached_property
    def full_expression(self):
        """ full composed model expression """
        def _generate_parts():
            components = iter(self.components)
            try:
                scale, model = next(components)
            except StopIteration:
                return
            sign = "- " if scale < 0 else ""
            yield f"{sign}{model.short_expression}"
            for scale, model in components:
                sign = "-" if scale < 0 else "+"
                yield "{sign} {model.short_expression}"

        return " ".join(_generate_parts())

    @cached_property
    def short_expression(self):
        """ short model expression """
        name = self.name
        if "-" in name:
            name = f"'{name}'"
        return name

    @cached_property
    def validity(self):
        """ Get model validity period. """
        if not self.components: # empty composed model
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

        def _iterate_models(model_obj, scale=1.0):
            """ iterate models of of a model object. """
            if isinstance(model_obj, SourceMagneticModel):
                yield model_obj.model, scale, model_obj.parameters
            elif isinstance(model_obj, ComposedMagneticModel):
                for item_scale, item_model_obj in model_obj.components:
                    for item in _iterate_models(item_model_obj, item_scale*scale):
                        yield item

        aggregated_model = ComposedGeomagneticModel()
        for model, scale, parameters in _iterate_models(self):
            aggregated_model.push(model, scale, **parameters)

        return aggregated_model

    @cached_property
    def sources(self):
        """ Get model sources and their validity ranges. """
        return list(chain.from_iterable(
            model.sources for _, model in self.components
        ))

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            model_name = self.extra["model_name"]
            return f"{model_name}: {msg}", kwargs

    def __init__(self, name, components, logger=None):
        super().__init__()
        self.name = name
        self.components = components
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": self.variables[0],
        })

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        output_ds = Dataset()

        if not variables:
            return output_ds

        b_nec = zeros((dataset.length, 3))
        for variable, (sign, _) in zip(self.required_variables, self.components):
            b_nec_source = dataset[variable]
            if sign < 0:
                b_nec -= b_nec_source
            else:
                b_nec += b_nec_source

        for variable in variables:
            filter_, type_, attrib = self._output[variable]
            output_ds.set(variable, filter_(b_nec), type_, attrib)

        return output_ds

    @cached_property
    def _output(self):
        f_var, b_var = self.variables
        return {
            f_var: (vnorm, CDF_DOUBLE_TYPE, {
                "DESCRIPTION": (
                    "Magnetic field intensity, calculated by "
                    f"the {self.name} spherical harmonic model"
                ),
                "UNITS": "nT",
            }),
            b_var: (lambda r: r, CDF_DOUBLE_TYPE, {
                "DESCRIPTION": (
                    "Magnetic field vector, NEC frame, calculated by "
                    f"the {self.name} spherical harmonic model"
                ),
                "UNITS": "nT",
            }),
        }
