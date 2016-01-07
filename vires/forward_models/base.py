#-------------------------------------------------------------------------------
# $Id$
#
# Project: EOxServer <http://eoxserver.org>
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

from datetime import datetime, timedelta

from django.utils.timezone import make_aware, utc
from eoxserver.core import Component, implements
import eoxmagmod
import numpy
import math

from vires.interfaces import ForwardModelProviderInterface
from vires.util import get_total_seconds

DG2RAD = math.pi / 180.0

def decimal_to_datetime(raw_value):
    """ Converts a decimal year representation to a Python datetime.
    """
    year = int(raw_value)
    rem = raw_value - year

    base = make_aware(datetime(year, 1, 1), utc)
    return base + timedelta(
        seconds=get_total_seconds(base.replace(year=base.year + 1) - base) * rem
    )

def diff_row(arr, step=1.0):
        """ Diferentiate 2D array along the row."""
        rstep = 1.0/step
        diff = numpy.empty(arr.shape)
        diff[:,1:-1,...] = 0.5*rstep*(arr[:,2:,...] - arr[:,:-2,...])
        diff[:,0,...] = rstep*(arr[:,1,...] - arr[:,0,...])
        diff[:,-1,...] = rstep*(arr[:,-1,...] - arr[:,-2,...])
        return diff


class BaseForwardModel(Component):
    """ Abstract base class for forward model providers using the eoxmagmod
        library.
    """

    implements(ForwardModelProviderInterface)

    abstract = True


    def evaluate(self, data_item, field, bbox, size_x, size_y, elevation, date, coeff_min=None, coeff_max=None):
        model = self.get_model(data_item)
        lons = numpy.linspace(bbox[0], bbox[2], size_x, endpoint=True)
        lats = numpy.linspace(bbox[3], bbox[1], size_y, endpoint=True)

        lons, lats = numpy.meshgrid(lons, lats)

        arr = numpy.empty((size_y, size_x, 3))
        arr[:, :, 0] = lats
        arr[:, :, 1] = lons
        arr[:, :, 2] = elevation
        dlon = (bbox[2] - bbox[0])/size_x

        coeff_min = coeff_min if coeff_min is not None else -1
        coeff_max = coeff_max if coeff_max is not None else -1

        values = model.eval(arr, date, maxdegree=coeff_max, mindegree=coeff_min, check_validity=False)
        if field == "F":
            return eoxmagmod.vnorm(values)
        elif field == "H":
            return eoxmagmod.vnorm(values[..., 0:2])

        elif field == "X":
            return values[..., 0]
        elif field == "Y":
            return values[..., 1]
        elif field == "Z":
            return (values[..., 2]*-1)
        elif field == "I":
            return eoxmagmod.vincdecnorm(values)[0]
        elif field == "D":
            return eoxmagmod.vincdecnorm(values)[1]
        elif field == "X_EW":
            coord_sph = eoxmagmod.convert(arr, eoxmagmod.GEODETIC_ABOVE_WGS84, eoxmagmod.GEOCENTRIC_SPHERICAL)
            # derivative along the easting coordinate
            rdist = 1.0/((dlon*DG2RAD)*coord_sph[:,:,2]*numpy.cos(coord_sph[:,:,0]*DG2RAD))
            return diff_row(values[...,0], 1.0)*rdist
        elif field == "Y_EW":
            coord_sph = eoxmagmod.convert(arr, eoxmagmod.GEODETIC_ABOVE_WGS84, eoxmagmod.GEOCENTRIC_SPHERICAL)
            rdist = 1.0/((dlon*DG2RAD)*coord_sph[:,:,2]*numpy.cos(coord_sph[:,:,0]*DG2RAD))
            return diff_row(values[...,1], 1.0)*rdist
        elif field == "Z_EW":
            coord_sph = eoxmagmod.convert(arr, eoxmagmod.GEODETIC_ABOVE_WGS84, eoxmagmod.GEOCENTRIC_SPHERICAL)
            rdist = 1.0/((dlon*DG2RAD)*coord_sph[:,:,2]*numpy.cos(coord_sph[:,:,0]*DG2RAD))
            return diff_row(values[...,2], 1.0)*rdist

        else:
            raise Exception("Invalid field '%s'." % field)

    @property
    def time_validity(self):
        return map(decimal_to_datetime, self.get_model(None).validity)

    def get_model(self):
        """ Interface method. Shall return any model from the eoxmagmod
            library.
        """
        raise NotImplementedError
