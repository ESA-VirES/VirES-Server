#-------------------------------------------------------------------------------
#
# Data Source - solar position
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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
#pylint: disable=too-many-locals

from math import pi
from logging import getLogger, LoggerAdapter
from numpy import hstack, ones, array, dot, arcsin
from eoxmagmod import (
    vnorm, convert, GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN,
)
from vires.util import include, unique, get_model
from vires.cdf_util import (
    cdf_rawtime_to_datetime,
    CDF_DOUBLE_TYPE,
)
from vires.dataset import Dataset
from vires.time_util import datetime_mean, datetime_to_decimal_year
from .model import Model

RAD2DEG = 180.0/pi


class DipoleTiltAnglePosition(Model):
    """ Dipole tilt angle calculation.
    The dipole tilt angle is 0 if the dipole axis is perpendicular
    to the Earth-Sun line and positive if the dipole axis is inclined towards
    Sun. The dipole tilt angle is in degrees.
    """
    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "Longitude", "SunDeclination", "SunHourAngle",
    ]

    VARIABLES = {
        "DipoleTiltAngle": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Dipole tilt angle',
            'UNITS': 'deg',
        }),
        "SunVector": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': (
                'Unit vector pointing to Sun in geocentric '
                'Cartesian coordinate system.'
            ),
            'UNITS': '-',
        }),
        "DipoleAxisVector": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': (
                'Dipole axis - north-pointing unit vector in geocentric '
                'Cartesian coordinate system.'
            ),
            'UNITS': '-',
        }),
    }

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'DipoleTiltAngle: %s' % msg, kwargs

    def __init__(self, model="IGRF", logger=None, varmap=None):

        if isinstance(model, basestring):
            self.model_name = model
            self.model = get_model(model)
        else:
            self.model_name = model.name
            self.model = model.model

        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    @property
    def variables(self):
        return list(self.VARIABLES)

    @property
    def required_variables(self):
        return self._required_variables

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)

        output_ds = Dataset()

        if variables:
            req_var = self.required_variables
            times, longitude, sundecl, sunhang = (
                dataset[var] for var in req_var[:4]
            )
            times_cdf_type = dataset.cdf_type.get(req_var[0], None)

            earth_sun_vector = convert(
                hstack((
                    sundecl.reshape((sundecl.size, 1)),
                    (longitude - sunhang).reshape((sunhang.size, 1)),
                    ones((sundecl.size, 1))
                )),
                GEOCENTRIC_SPHERICAL,
                GEOCENTRIC_CARTESIAN,
            )

            if len(times) > 0:
                start = cdf_rawtime_to_datetime(min(times), times_cdf_type)
                stop = cdf_rawtime_to_datetime(max(times), times_cdf_type)
                mean_time = datetime_mean(start, stop)
                mean_time_dy = datetime_to_decimal_year(mean_time)
                self.logger.debug("requested time-span %s, %s", start, stop)
                self.logger.debug(
                    "applied mean time %s (%s)", mean_time, mean_time_dy
                )
            else:
                mean_time_dy = 2000.0 # default in case of an empty time array

            # construct north pointing unit vector of the dipole axis
            # from the spherical harmonic coefficients
            self.logger.debug("extracting dipole axis from %s", self.model_name)
            coef_g, coef_h = self.model.get_coef_static(mean_time_dy)
            north_pole_vector = array([coef_g[2], coef_h[2], coef_g[1]])
            north_pole_vector /= -vnorm(north_pole_vector)

            for variable in variables:
                cdf_type, cdf_attr = self.VARIABLES[variable]
                if variable == "DipoleTiltAngle":
                    output_ds.set(variable, RAD2DEG*arcsin(dot(
                        earth_sun_vector,
                        north_pole_vector.reshape((3, 1))
                    ).ravel()), cdf_type, cdf_attr)
                elif variable == "SunVector":
                    output_ds.set(variable, earth_sun_vector, cdf_type, cdf_attr)
                elif variable == "DipoleAxisVector":
                    output_ds.set(variable, dot(
                        ones((times.size, 1)),
                        north_pole_vector.reshape((1, 3))
                    ), cdf_type, cdf_attr)

        return output_ds
