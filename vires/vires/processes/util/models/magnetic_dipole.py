#-------------------------------------------------------------------------------
#
# Data Source - magnetic dipole and dipole tilt angle
#
# Authors: Martin Paces <martin.paces@eox.at>
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
from numpy import empty, broadcast_to, arcsin, arctan2
from eoxmagmod import vnorm
from vires.util import LazyString, pretty_list
from vires.time_util import format_datetime
from vires.cdf_util import (
    cdf_rawtime_to_mjd2000,
    CDF_DOUBLE_TYPE,
)
from vires.dataset import Dataset
from vires.time_util import mjd2000_to_datetime
from vires.magnetic_models import MODEL_CACHE, DIPOLE_MODEL
from .base import Model

RAD2DEG = 180.0/pi


class MagneticDipole(Model):
    """ Magnetic dipole, north magnetic pole coordinates calculation.
    """
    DEFAULT_REQUIRED_VARIABLES = ["Timestamp"]

    VARIABLES = {
        "DipoleAxisVector": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': (
                'Dipole axis - north-pointing unit vector in geocentric '
                'Cartesian coordinate system.'
            ),
            'UNITS': '-',
        }),
        "NGPLatitude": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': "North Geomagnetic Pole latitude.",
            'UNITS': 'deg',
        }),
        "NGPLongitude": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': "North Geomagnetic Pole longitude.",
            'UNITS': 'deg',
        }),
    }

    @property
    def variables(self):
        return ["DipoleAxisVector", "NGPLatitude", "NGPLongitude"]

    @property
    def required_variables(self):
        return list(self._required_variables)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return f"MageticDipole: {msg}", kwargs

    def __init__(self, model=DIPOLE_MODEL, logger=None, varmap=None):
        super().__init__()
        if isinstance(model, str):
            self.model_name = model
            self.model = MODEL_CACHE.get_model(model)
        else:
            self.model_name = model.name
            self.model = model.model
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def _extract_required_variables(self, dataset):
        times, = self.required_variables
        return cdf_rawtime_to_mjd2000(dataset[times], dataset.cdf_type[times])

    @staticmethod
    def _eval_dipole_tilt_angle(earth_sun_vector, north_pole_vector):
        return RAD2DEG * arcsin(
            (earth_sun_vector * north_pole_vector).sum(axis=1)
        )

    def _eval_dipole_axis(self, times):
        if times.size == 0:
            return empty((0, 3))

        time_start, time_end = times.min(), times.max()
        mean_time = 0.5*(time_start + time_end)

        self.logger.debug("requested time-span: %s", LazyString(lambda: (
            f"{format_datetime(mjd2000_to_datetime(time_start))}/"
            f"{format_datetime(mjd2000_to_datetime(time_end))}"
        )))
        self.logger.debug(
            "applied mean time: %s", LazyString(lambda: (
            f"{format_datetime(mjd2000_to_datetime(mean_time))}"
            f" (MJD: {mean_time})"
        )))

        # construct north pointing unit vector of the dipole axis
        # from the spherical harmonic coefficients
        self.logger.debug("extracting dipole axis from %s", self.model_name)

        coeff, _ = self.model.coefficients(mean_time, max_degree=1)
        north_pole_vector = coeff[[2, 2, 1], [0, 1, 0]]
        north_pole_vector *= -1.0/vnorm(north_pole_vector)

        return broadcast_to(north_pole_vector, (times.size, 3))

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = set(self.variables if variables is None else variables)
        self.logger.debug(
            "requested variables: %s",
            pretty_list(set(self.variables) & variables)
        )

        if not variables:
            return output_ds

        times = self._extract_required_variables(dataset)
        north_pole_vector = self._eval_dipole_axis(times)

        def _set_output(variable, data):
            output_ds.set(variable, data, *self.VARIABLES[variable])

        (
            north_pole_vector_variable, ngp_latitude_variable,
            ngp_longitude_variable,
        ) = self.variables

        if north_pole_vector_variable in variables:
            _set_output(north_pole_vector_variable, north_pole_vector)

        if ngp_latitude_variable in variables:
            ngp_latitude = RAD2DEG*arcsin(north_pole_vector[..., 2])
            _set_output(ngp_latitude_variable, ngp_latitude)

        if ngp_longitude_variable in variables:
            ngp_longitude = RAD2DEG*arctan2(
                north_pole_vector[..., 1], north_pole_vector[..., 0]
            )
            _set_output(ngp_longitude_variable, ngp_longitude)

        return output_ds


class DipoleTiltAngle(Model):
    """ Magnetic dipole tilt angle calculation.
    The dipole tilt angle is 0 if the dipole axis is perpendicular
    to the Earth-Sun line and positive if the dipole axis is inclined towards
    Sun. The dipole tilt angle is in degrees.
    """
    DEFAULT_REQUIRED_VARIABLES = ["SunVector", "DipoleAxisVector"]

    VARIABLES = {
        "DipoleTiltAngle": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Dipole tilt angle',
            'UNITS': 'deg',
        }),
    }

    @property
    def variables(self):
        return ["DipoleTiltAngle"]

    @property
    def required_variables(self):
        return list(self._required_variables)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return f"DipoleTiltAngle: {msg}", kwargs

    def __init__(self, logger=None, varmap=None):
        super().__init__()
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def _extract_required_variables(self, dataset):
        sunvect, dipvect = self.required_variables
        return dataset[sunvect], dataset[dipvect]

    @staticmethod
    def _eval_dipole_tilt_angle(earth_sun_vector, north_pole_vector):
        return RAD2DEG * arcsin(
            (earth_sun_vector * north_pole_vector).sum(axis=1)
        )


    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = set(self.variables if variables is None else variables)
        self.logger.debug(
            "requested variables: %s",
            pretty_list(set(self.variables) & variables)
        )

        if not variables:
            return output_ds

        earth_sun_vector, north_pole_vector = (
            self._extract_required_variables(dataset)
        )

        dipole_tilt_angle = self._eval_dipole_tilt_angle(
            earth_sun_vector, north_pole_vector
        )

        def _set_output(variable, data):
            output_ds.set(variable, data, *self.VARIABLES[variable])

        dipole_tilt_angle_variable, = self.variables
        _set_output(dipole_tilt_angle_variable, dipole_tilt_angle)

        return output_ds
