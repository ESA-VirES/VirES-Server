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

from logging import getLogger, LoggerAdapter
from itertools import chain
from numpy import stack, searchsorted
from eoxmagmod import vnorm
from vires.util import include, unique, cached_property, pretty_list
from vires.cdf_util import cdf_rawtime_to_mjd2000, CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from ..base import Model


class SourceMagneticModel(Model):
    """ Source forward spherical harmonic expansion model. """

    # The dependencies are composed from the requirements of the source
    # model. This is the mapping of the requirements to the actual variables.
    SOURCE_VARIABLES = {
        "time": ["Timestamp"],
        "location": ["Latitude", "Longitude", "Radius"],
        "f107": ["F107_avg81d"],
        "f107_instant": ["F107"],
        "subsolar_point": ["SunDeclination", "SunLongitude"],
        "amps": ["IMF_BY_GSM", "IMF_BZ_GSM", "IMF_V", "DipoleTiltAngle"],
    }

    #BASE_VARIABLES = ["F", "B_NEC"]
    BASE_VARIABLES = ["B_NEC"]

    @cached_property
    def variables(self):
        return [f"{variable}_{self.name}" for variable in self.BASE_VARIABLES]

    @cached_property
    def required_variables(self):
        return list(chain.from_iterable(
            variables for variables in self._source_variables.values()
        ))

    @cached_property
    def name(self):
        """ composed model name """
        return self.source_model.name

    @cached_property
    def expression(self):
        """ short model expression """
        return self.source_model.expression

    @cached_property
    def model(self):
        """ Get the low-level magnetic model. """
        return self.source_model.model

    @property
    def validity(self):
        """ Get model validity period. """
        return self.source_model.validity

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            model_name = self.extra["model_name"]
            return f"{model_name}: {msg}", kwargs

    def __init__(self, source_model, logger=None, varmap=None):
        super().__init__()

        # an instance of parsed vires.magnetic_models.parser.SourceMagneticModel
        self.source_model = source_model

        varmap = varmap or {}

        available_data_extractors = {
            "time": self._extract_time,
            "location": self._extract_location,
            "f107": self._extract_f107,
            "f107_instant": self._extract_f107_instant,
            "subsolar_point": self._extract_subsolar_point,
            "amps": self._extract_amps_inputs,
        }

        self.data_extractors = [
            available_data_extractors[requirement]
            for requirement in source_model.model.parameters
        ]

        self._source_variables = {
            requirement: [
                varmap.get(var, var) for var
                in self.SOURCE_VARIABLES[requirement]
            ]
            for requirement in source_model.model.parameters
        }

        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": self.name,
        })

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", pretty_list(variables))
        output_ds = Dataset()

        if variables:
            inputs = {"scale": [1, 1, -1]}
            for extract in self.data_extractors:
                inputs.update(extract(dataset))
            inputs.update(self.source_model.parameters)

            result = self.model.eval(**inputs)
            times = inputs['time']
            if times.size > 0:
                self.product_set.update(
                    self._extract_sources(times[0], times[-1])
                )

            for variable in variables:
                filter_, type_, attrib = self._output[variable]
                output_ds.set(variable, filter_(result), type_, attrib)

        return output_ds

    @cached_property
    def _output(self):
        #f_var, b_var = self.variables
        b_var, = self.variables
        return {
            #f_var: (vnorm, CDF_DOUBLE_TYPE, {
            #    "DESCRIPTION": (
            #        "Magnetic field intensity, calculated by "
            #        f"the {self.name} spherical harmonic model"
            #    ),
            #    "UNITS": "nT",
            #}),
            b_var: (lambda r: r, CDF_DOUBLE_TYPE, {
                "DESCRIPTION": (
                    "Magnetic field vector, NEC frame, calculated by "
                    f"the {self.name} spherical harmonic model"
                ),
                "UNITS": "nT",
            }),
        }

    def _extract_sources(self, start, end):
        """ Extract a subset of sources matched my the given time interval. """
        validity_start, validity_end = self.validity
        start = max(start, validity_start)
        end = min(end, validity_end)
        product_set = set()
        for sources in self.source_model.extract_sources(start, end):
            product_set.update(sources.names)
        return product_set

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

    def _extract_f107_instant(self, dataset):
        f107_instant, = self._source_variables["f107_instant"]
        return [
            ("f107_instant", dataset[f107_instant]),
        ]

    def _extract_subsolar_point(self, dataset):
        lat_sol, lon_sol = self._source_variables["subsolar_point"]
        return [
            ("lat_sol", dataset[lat_sol]),
            ("lon_sol", dataset[lon_sol]),
        ]

    def _extract_amps_inputs(self, dataset):
        imf_by, imf_bz, imf_v, tilt_anlge = self._source_variables["amps"]
        return [
            ("imf_by", dataset[imf_by]),
            ("imf_bz", dataset[imf_bz]),
            ("imf_v", dataset[imf_v]),
            ("tilt_angle", dataset[tilt_anlge]),
        ]
