#-------------------------------------------------------------------------------
#
#  Base forward expansion model class.
#
# Project: VirES
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

import math
from numpy import cos, meshgrid, empty, linspace, tile

from eoxserver.core import Component, implements
from eoxmagmod import (
    vnorm, convert, vincdecnorm,
    GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
)

from vires.interfaces import ForwardModelProviderInterface
from vires.time_util import decimal_year_to_datetime, naive_to_utc

DG2RAD = math.pi / 180.0

def diff_row(array):
    """ Diferentiate 2D arrayay columns along the row."""
    diff = empty(array.shape)
    # inner rows
    diff[:, 1:-1, ...] = 0.5 * (array[:, 2:, ...] - array[:, :-2, ...])
    # border rows
    diff[:, 0, ...] = array[:, 1, ...] - array[:, 0, ...]
    diff[:, -1, ...] = array[:, -1, ...] - array[:, -2, ...]
    return diff


def dist_ew(coord_gdt):
    """ East-West sample distances. """
    # first column Geocentric spherical coordinates in degrees
    col_coord_sph = convert(
        coord_gdt[:, 0, :], GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL
    )
    # convert spherical latitudes to radians
    col_coord_sph[:, 0] *= DG2RAD
    # longitude differences in radians
    diff_lon = DG2RAD * (coord_gdt[0, 1, 1] - coord_gdt[0, 0, 1])
    # distance between samples
    dist = diff_lon * col_coord_sph[:, 2] * cos(col_coord_sph[:, 0])
    return tile(dist.reshape(dist.size, 1), (1, coord_gdt.shape[0]))


class BaseForwardModel(Component):
    """ Abstract base class for forward model providers using the eoxmagmod
        library.
    """
    implements(ForwardModelProviderInterface)
    abstract = True

    def evaluate(self, data_item, field, bbox, size_x, size_y, elevation,
                 date, coeff_min=None, coeff_max=None):
        """ Evaluate forward expansion model.
        Inputs:
            data_item - ???
            field - identifier of the property to be evaluated.
                    Possible values are:
                        F - magnetic field intensity
                        H - intensity of the ground tangential magnetic field
                            component
                        X - easting magnetic field component
                        Y - northing magnetic field component
                        Z - down-pointing magnetic field component
                        I - magnetic field inclination
                        D - magnetic field declination
                        X_EW - easting magnetic field component derivative
                               along the easting coordinate
                        Y_EW - northing magnetic field component derivative
                               along the easting coordinate
                        Z_EW - down-pointing magnetic field component derivative
                               along the easting coordinate
            bbox - AoI extent bounding box (min_lon, min_lat, max_lon, max_lat)
            size_x - number of samples longitude row
            size_y - number of samples latitude column
            elevation - elevation elevation above to WGS84 ellipsoid
            date - decimal Julian date (e.g., 2016.2345)
            coeff_min - optional minimal coefficient trim
            coeff_max - optional maximum coefficient trim

        Output:
            Rectangular array of size_x by size_y elements.
        """
        hd_x = (0.5 / size_x) * (bbox[2] - bbox[0])
        hd_y = (0.5 / size_y) * (bbox[3] - bbox[1])
        lons, lats = meshgrid(
            linspace(bbox[0] + hd_x, bbox[2] - hd_x, size_x, endpoint=True),
            linspace(bbox[3] + hd_y, bbox[1] - hd_y, size_y, endpoint=True)
        )

        # Geodetic coordinates with elevation above the WGS84 ellipsoid.
        coord_gdt = empty((size_y, size_x, 3))
        coord_gdt[:, :, 0] = lats
        coord_gdt[:, :, 1] = lons
        coord_gdt[:, :, 2] = elevation

        coeff_min = coeff_min if coeff_min is not None else -1
        coeff_max = coeff_max if coeff_max is not None else -1

        # Evaluate the magnetic field vector components
        # (northing, easting, up-pointing)
        field_components = self.model.eval(
            coord_gdt, date, GEODETIC_ABOVE_WGS84, GEODETIC_ABOVE_WGS84,
            maxdegree=coeff_max, mindegree=coeff_min, check_validity=False
        )

        if field == "F":
            # magnetic field intensity
            return vnorm(field_components)
        elif field == "H":
            # intensity of the ground tangential magnetic field component
            return vnorm(field_components[..., 0:2])
        elif field == "X":
            # easting magnetic field component
            return field_components[..., 0]
        elif field == "Y":
            # northing magnetic field component
            return field_components[..., 1]
        elif field == "Z":
            # down-pointing magnetic field component
            return -field_components[..., 2]
        elif field == "I":
            # magnetic field inclination
            return vincdecnorm(field_components)[0]
        elif field == "D":
            # magnetic field inclination
            return vincdecnorm(field_components)[1]
        elif field == "X_EW":
            # easting magnetic field component derivative
            # along the easting coordinate
            return diff_row(field_components[..., 1]) / dist_ew(coord_gdt)
        elif field == "Y_EW":
            # northing magnetic field component derivative
            # along the easting coordinate
            return diff_row(field_components[..., 1]) / dist_ew(coord_gdt)
        elif field == "Z_EW":
            # northing magnetic field component derivative
            # along the easting coordinate
            return diff_row(-field_components[..., 2]) / dist_ew(coord_gdt)
        else:
            raise Exception("Invalid field '%s'." % field)

    @property
    def time_validity(self):
        """ Get the validity interval of the model. """
        return [
            naive_to_utc(decimal_year_to_datetime(dy))
            for dy in self.model.validity
        ]

    @property
    def model(self):
        """ Get model object. (Abstract method.)"""
        raise NotImplementedError
