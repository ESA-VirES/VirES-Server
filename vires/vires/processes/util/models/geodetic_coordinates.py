#-------------------------------------------------------------------------------
#
# Data Source - conversion of geodetic to geocentric coordinates
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2022 EOX IT Services GmbH
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
from numpy import stack
from eoxmagmod import (
    convert, GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
)
from vires.util import include, unique
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class Geodetic2GeocentricCoordinates(Model):
    """ Model converting geodetic to geocentric coordinates. """
    DEFAULT_REQUIRED_VARIABLES = [
        "Latitude_GD", "Longitude_GD", "Height_GD",
    ]

    VARIABLES = {
        "Latitude": {
            "DESCRIPTION": "Position in ITRF - Latitude",
            "UNITS": "deg"
        },
        "Longitude": {
            "DESCRIPTION": "Position in ITRF - Longitude",
            "UNITS": "deg"
        },
        "Radius": {
            "DESCRIPTION": "Position in ITRF - Radius",
            "UNITS": "m"
        },
    }

    @property
    def variables(self):
        return list(self.VARIABLES)

    @property
    def required_variables(self):
        return list(self._required_variables)

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'GD2GC: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super().__init__()
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    def _extract_required_variables(self, dataset):
        latitude_gd, longitude_gd, height_gd = self._required_variables
        return (
            dataset[latitude_gd], dataset[longitude_gd], dataset[height_gd],
        )

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)
        if variables:
            self.logger.debug("requested dataset length %s", dataset.length)

            # extract geodetic coordinates
            gd_lat, gd_lon, gd_height = self._extract_required_variables(dataset)

            # convert geodetic to geocentric coordinates
            # (height is converted to kilometres)
            gc_coords = convert(
                stack((gd_lat, gd_lon, 1e-3*gd_height), axis=1),
                GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
            )

            outputs = zip(self.variables, (
                gc_coords[..., 0], # latitude in deg
                gc_coords[..., 1], # longitude in deg
                1e3*gc_coords[..., 2], # convert radius to metres
            ))

            for variable, data in outputs:
                if variable in variables:
                    output_ds.set(
                        variable, data, CDF_DOUBLE_TYPE, self.VARIABLES[variable]
                    )

        return output_ds
