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
from numpy import ones, arcsin, stack, broadcast_to
from eoxmagmod import (
    vnorm, convert, GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN,
)
from vires.cdf_util import (
    cdf_rawtime_to_mjd2000,
    CDF_DOUBLE_TYPE,
)
from vires.dataset import Dataset
from vires.time_util import mjd2000_to_datetime
from .model import Model
from .magnetic_models import get_model

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
        return list(self._required_variables)

    def _extract_required_variables(self, dataset):
        times, longitude, sundecl, sunhang = self.required_variables
        return (
            cdf_rawtime_to_mjd2000(dataset[times], dataset.cdf_type[times]),
            dataset[longitude], dataset[sundecl], dataset[sunhang],
        )

    @staticmethod
    def _eval_dipole_tilt_angle(earth_sun_vector, north_pole_vector):
        return RAD2DEG * arcsin(
            (earth_sun_vector * north_pole_vector).sum(axis=1)
        )

    @staticmethod
    def _eval_earth_sun_vector(longitude, sundecl, sunhang):
        return convert(
            stack((sundecl, (longitude - sunhang), ones(sundecl.size)), axis=1),
            GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN
        )

    def _eval_dipole_axis(self, times):
        if times.size == 0:
            broadcast_to([0, 0, 0], (0, 3))


        time_start, time_end = times.min(), times.max()
        mean_time = 0.5*(time_start + time_end)

        self.logger.debug(
            "requested time-span %s, %s",
            mjd2000_to_datetime(time_start),
            mjd2000_to_datetime(time_end)
        )
        self.logger.debug(
            "applied mean time %s (%s)",
            mjd2000_to_datetime(mean_time), mean_time
        )

        # construct north pointing unit vector of the dipole axis
        # from the spherical harmonic coefficients
        self.logger.debug("extracting dipole axis from %s", self.model_name)

        coeff = self.model.coefficients(mean_time, max_degree=1)
        north_pole_vector = coeff[[2, 2, 1], [0, 1, 0]]
        north_pole_vector *= -1.0/vnorm(north_pole_vector)

        return broadcast_to(north_pole_vector, (times.size, 3))

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = set(self.variables if variables is None else variables)
        self.logger.debug(
            "requested variables %s", list(set(self.variables) & variables)
        )

        (
            dipole_tilt_angle_variable,
            earth_sun_vector_variable,
            north_pole_vector_variable,
        ) = self.variables

        _produce_dipole_tilt_angle = dipole_tilt_angle_variable in variables
        _produce_earth_sun_vector = earth_sun_vector_variable in variables
        _produce_north_pole_vector = north_pole_vector_variable in variables

        def _set_output(variable, data):
            output_ds.set(variable, data, *self.VARIABLES[variable])

        times, longitude, sundecl, sunhang = (
            self._extract_required_variables(dataset)
        )

        if _produce_dipole_tilt_angle or _produce_earth_sun_vector:
            earth_sun_vector = self._eval_earth_sun_vector(
                longitude, sundecl, sunhang
            )

        if _produce_dipole_tilt_angle or _produce_north_pole_vector:
            north_pole_vector = self._eval_dipole_axis(times)

        if _produce_dipole_tilt_angle:
            dipole_tilt_angle = self._eval_dipole_tilt_angle(
                earth_sun_vector, north_pole_vector
            )
            _set_output(dipole_tilt_angle_variable, dipole_tilt_angle)

        if _produce_earth_sun_vector:
            _set_output(earth_sun_vector_variable, earth_sun_vector)

        if _produce_north_pole_vector:
            _set_output(north_pole_vector_variable, north_pole_vector)

        return output_ds
