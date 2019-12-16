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
#pylint: disable=too-many-locals,too-many-arguments,missing-docstring
#pylint: disable=too-few-public-methods

from logging import getLogger, LoggerAdapter
from itertools import chain
from numpy import stack, inf, zeros, searchsorted
from eoxmagmod import vnorm, ComposedGeomagneticModel
from vires.util import include, unique, cached_property
from vires.cdf_util import cdf_rawtime_to_mjd2000, CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class MagneticModelResidual(Model):
    """ Residual evaluation. """

    @cached_property
    def variables(self):
        return ["%s_res_%s" % (self.variable, self.model_name)]

    @cached_property
    def required_variables(self):
        return [self.variable, "%s_%s" % (self.variable, self.model_name)]

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["residual_name"], msg), kwargs

    def __init__(self, model_name, variable, logger=None):
        super(MagneticModelResidual, self).__init__()
        self.model_name = model_name
        self.variable = variable
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "residual_name": self.variables[0],
        })

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        output_variable, = self.variables
        is_requested = variables is None or output_variable in variables
        self.logger.debug(
            "requested variables %s", self.variables if is_requested else []
        )
        if is_requested:
            self.logger.debug("requested dataset length %s", dataset.length)
            measurement_variable, model_variable = self.required_variables
            output_ds.set(
                output_variable,
                dataset[measurement_variable] - dataset[model_variable],
                dataset.cdf_type[measurement_variable],
                self._get_attributes(dataset, measurement_variable),
            )
        return output_ds

    def _get_attributes(self, dataset, variable):
        src_attr = dataset.cdf_attr.get(variable)
        if not src_attr:
            return None

        if variable == "B_NEC":
            base = 'Magnetic field vector residual, NEC frame'
        else:
            base = 'Magnetic field intensity residual'

        return {
            'DESCRIPTION': (
                '%s, calculated as a difference of the measurement and '
                'value of the %s spherical harmonic model' %
                (base, self.model_name)
            ),
            'UNITS': src_attr['UNITS']
        }


class ExtractSourcesMixIn(object):
    """ Mix-in class defining the extract sources method. """

    def extract_sources(self, start, end):
        """ Extract set of sources matched my the given time interval. """
        validity_start, validity_end = self.validity
        start = max(start, validity_start)
        end = min(end, validity_end)

        product_set = set()

        if start > end:
            return product_set # not overlap

        for source_list, ranges in self.sources:
            if source_list:
                idx_start = max(0, searchsorted(ranges[:, 1], start, 'left'))
                idx_stop = searchsorted(ranges[:, 0], end, 'right')
                product_set.update(source_list[idx_start:idx_stop])

        return product_set


class ComposedMagneticModel(Model, ExtractSourcesMixIn):
    """ Combined forward spherical harmonic expansion model. """
    BASE_VARIABLES = ["F", "B_NEC"]

    @cached_property
    def variables(self):
        return [
            "%s_%s" % (variable, self.name) for variable in self.BASE_VARIABLES
        ]

    @cached_property
    def required_variables(self):
        return ["B_NEC_%s" % model.name for _, model in self.components]

    @cached_property
    def full_expression(self):
        """ full composed model expression """
        def _generate_parts():
            components = iter(self.components)
            scale, model = next(components)
            yield "%s%s" % ("- " if scale < 0 else "", model.short_expression)
            for scale, model in components:
                yield "%s %s" % (
                    "-" if scale < 0 else "+", model.short_expression
                )

        return " ".join(_generate_parts())

    @cached_property
    def short_expression(self):
        """ short model expression """
        name = self.name
        if '-' in name:
            name = "'%s'" % name
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
            return '%s: %s' % (self.extra["model_name"], msg), kwargs

    def __init__(self, name, components, logger=None):
        super(ComposedMagneticModel, self).__init__()
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
                'DESCRIPTION': (
                    'Magnetic field intensity, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            }),
            b_var: (lambda r: r, CDF_DOUBLE_TYPE, {
                'DESCRIPTION': (
                    'Magnetic field vector, NEC frame, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            }),
        }


class SourceMagneticModel(Model, ExtractSourcesMixIn):
    """ Source forward spherical harmonic expansion model. """
    SOURCE_VARIABLES = {
        "time": ["Timestamp"],
        "location": ["Latitude", "Longitude", "Radius"],
        "f107": ["F107"],
        "subsolar_point": ["SunDeclination", "SunLongitude"],
        "amps": [
            "F10_INDEX", "IMF_BY_GSM", "IMF_BZ_GSM", "IMF_V",
            "DipoleTiltAngle",
        ]
    }
    BASE_VARIABLES = ["F", "B_NEC"]

    @cached_property
    def variables(self):
        return [
            "%s_%s" % (variable, self.name) for variable in self.BASE_VARIABLES
        ]

    @staticmethod
    def _get_name(name, parameters):
        return "%s(%s)" % (name, ",".join(
            "%s=%s" % item for item in sorted(parameters.items())
        ))

    @cached_property
    def name(self):
        """ composed model name """
        return self._get_name(self.short_name, self.parameters)

    @property
    def short_expression(self):
        """ short model expression """
        name = self.short_name
        if "-" in name:
            name = "'%s'" % name
        return self._get_name(name, self.parameters)

    @cached_property
    def required_variables(self):
        return list(chain.from_iterable(
            variables for variables in self._source_variables.values()
        ))

    @property
    def validity(self):
        """ Get model validity period. """
        return self.model.validity

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["model_name"], msg), kwargs

    def __init__(self, model_name, model, sources=None, parameters=None,
                 logger=None, varmap=None):
        super(SourceMagneticModel, self).__init__()
        self.short_name = model_name
        self.model = model
        self.sources = sources or []
        self.parameters = parameters or {}
        varmap = varmap or {}

        available_data_extractors = {
            "time": self._extract_time,
            "location": self._extract_location,
            "f107": self._extract_f107,
            "subsolar_point": self._extract_subsolar_point,
            "amps": self._extract_amps_inputs,
        }

        self.data_extractors = [
            available_data_extractors[requirement]
            for requirement in model.parameters
        ]

        self._source_variables = {
            requirement: [
                varmap.get(var, var) for var
                in self.SOURCE_VARIABLES[requirement]
            ]
            for requirement in model.parameters
        }

        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": self.name,
        })

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        output_ds = Dataset()

        if variables:
            inputs = {"scale": [1, 1, -1]}
            for extract in self.data_extractors:
                inputs.update(extract(dataset))
            inputs.update(self.parameters)

            result = self.model.eval(**inputs)
            times = inputs['time']
            if times.size > 0:
                self.product_set.update(
                    self.extract_sources(times[0], times[-1])
                )

            for variable in variables:
                filter_, type_, attrib = self._output[variable]
                output_ds.set(variable, filter_(result), type_, attrib)

        return output_ds

    @cached_property
    def _output(self):
        f_var, b_var = self.variables
        return {
            f_var: (vnorm, CDF_DOUBLE_TYPE, {
                'DESCRIPTION': (
                    'Magnetic field intensity, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            }),
            b_var: (lambda r: r, CDF_DOUBLE_TYPE, {
                'DESCRIPTION': (
                    'Magnetic field vector, NEC frame, calculated by '
                    'the %s spherical harmonic model' % self.name
                ),
                'UNITS': 'nT',
            }),
        }

    def _extract_time(self, dataset):
        time, = self._source_variables["time"]
        return [
            ("time", cdf_rawtime_to_mjd2000(
                dataset[time], dataset.cdf_type[time]
            )),
        ]

    def _extract_location(self, dataset):
        latitude, longitude, radius = self._source_variables["location"]
        return [
            ("location", stack((
                # Note: radius is converted from metres to kilometres
                dataset[latitude], dataset[longitude], 1e-3*dataset[radius],
            ), axis=1)),
        ]

    def _extract_f107(self, dataset):
        f107, = self._source_variables["f107"]
        return [
            ("f107", dataset[f107]),
        ]

    def _extract_subsolar_point(self, dataset):
        lat_sol, lon_sol = self._source_variables["subsolar_point"]
        return [
            ("lat_sol", dataset[lat_sol]),
            ("lon_sol", dataset[lon_sol]),
        ]

    def _extract_amps_inputs(self, dataset):
        f107, imf_by, imf_bz, imf_v, tilt_anlge = self._source_variables["amps"]
        return [
            ("imf_f107", dataset[f107]),
            ("imf_by", dataset[imf_by]),
            ("imf_bz", dataset[imf_bz]),
            ("imf_v", dataset[imf_v]),
            ("tilt_angle", dataset[tilt_anlge]),
        ]
