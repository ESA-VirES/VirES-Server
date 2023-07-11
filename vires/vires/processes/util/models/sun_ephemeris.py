#-------------------------------------------------------------------------------
#
# Data Source - solar ephemeris
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
#pylint: disable=too-many-locals

from logging import getLogger, LoggerAdapter
from numpy import stack, ones
from eoxmagmod import sunpos, convert, GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN
from vires.util import include, unique, pretty_list
from vires.cdf_util import cdf_rawtime_to_mjd2000, CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class SunPosition(Model):
    """ Sun position model. """
    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "Latitude", "Longitude", "Radius",
    ]

    VARIABLES = {
        "SunDeclination": (0, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - declination', 'UNITS': 'deg',
        }),
        "SunRightAscension": (1, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - right ascension', 'UNITS': 'deg',
        }),
        "SunHourAngle": (2, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - hour angle', 'UNITS': 'deg',
        }),
        "SunAzimuthAngle": (3, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - azimuth angle', 'UNITS': 'deg',
        }),
        "SunZenithAngle": (4, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - zenith angle', 'UNITS': 'deg',
        }),
    }

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'SunPosition: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super().__init__()
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

    def _extract_required_variables(self, dataset):
        time, latitude, longitude, radius = self._required_variables
        # Note: radius is converted from metres to kilometres
        return (
            cdf_rawtime_to_mjd2000(dataset[time], dataset.cdf_type[time]),
            dataset[latitude], dataset[longitude], 1e-3*dataset[radius],
        )

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables: %s", pretty_list(variables))

        output_ds = Dataset()

        if variables:
            times, lats, lons, rads = self._extract_required_variables(dataset)
            # FIXME: UTC to TT offset
            result = sunpos(times, lats, lons, rads, 0)

            for variable in variables:
                idx, cdf_type, cdf_attr = self.VARIABLES[variable]
                output_ds.set(variable, result[idx], cdf_type, cdf_attr)

        return output_ds


class SubSolarPoint(Model):
    """ Dipole tilt angle calculation.
    The dipole tilt angle is 0 if the dipole axis is perpendicular
    to the Earth-Sun line and positive if the dipole axis is inclined towards
    Sun. The dipole tilt angle is in degrees.
    """
    DEFAULT_REQUIRED_VARIABLES = [
        "Longitude", "SunDeclination", "SunHourAngle",
    ]

    VARIABLES = {
        "SunLongitude": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': (
                'Longitude of the sub-solar point complementary '
                'to the SunDeclination (i.e., sub-solar longitude. '
            ),
            'UNITS': 'deg',
        }),
        "SunVector": (CDF_DOUBLE_TYPE, {
            'DESCRIPTION': (
                'Unit vector pointing to Sun in geocentric '
                'Cartesian coordinate system.'
            ),
            'UNITS': '-',
        }),
    }

    @property
    def variables(self):
        return ["SunLongitude", "SunVector"]

    @property
    def required_variables(self):
        return list(self._required_variables)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'SubSolarPoint: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super().__init__()
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def _extract_required_variables(self, dataset):
        longitude, sundecl, sunhang = self.required_variables
        return dataset[longitude], dataset[sundecl], dataset[sunhang]

    @staticmethod
    def _eval_earth_sun_vector(latitude, longitude):
        return convert(
            stack((latitude, longitude, ones(latitude.size)), axis=1),
            GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN
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

        longitude, declination, hour_angle = (
            self._extract_required_variables(dataset)
        )
        subsolar_longitude = longitude - hour_angle

        def _set_output(variable, data):
            output_ds.set(variable, data, *self.VARIABLES[variable])

        subsolar_longitude_variable, earth_sun_vector_variable = self.variables

        if subsolar_longitude_variable in variables:
            _set_output(subsolar_longitude_variable, subsolar_longitude)

        if earth_sun_vector_variable in variables:
            earth_sun_vector = self._eval_earth_sun_vector(
                declination, subsolar_longitude
            )
            _set_output(earth_sun_vector_variable, earth_sun_vector)

        return output_ds
