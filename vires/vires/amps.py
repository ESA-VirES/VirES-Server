#-------------------------------------------------------------------------------
#
# AMPS model integration
#
# Author: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=too-many-arguments

from numpy import asarray, prod, empty, broadcast_to, stack, datetime64
from eoxmagmod import (
    convert, vrotate, GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
    mjd2000_to_decimal_year,
)
from eoxmagmod.magnetic_model.model import GeomagneticModel
from pyamps import get_B_space

DT64_2000 = datetime64('2000-01-01', 'ms')

def mjd2000_to_dt64ms(mjd2000):
    """ Convert MJD2000 to numpy.datetime64 with millisecond precision. """
    try:
        return (
            (mjd2000 * 8.64e7).astype('int64').astype('timedelta64[ms]')
            + DT64_2000
        )
    except ValueError as error:
        raise ValueError("%s %r" % (error, mjd2000))


class AmpsMagneticFieldModel(GeomagneticModel):
    """ Abstract base class of the Earth magnetic field model. """
    user_parameters = ()
    parameters = ("time", "location", "f107", "amps")
    CHUNK_SIZE = 1200
    DEFAULT_EPOCH = 2015.0
    REFERENCE_HEIGHT = 110.0

    validity = (-36524.0, 7305.0) # 1900 - 2019

    def __init__(self, filename):
        self.filename = filename

    def eval(self, time, location,
             input_coordinate_system=GEOCENTRIC_SPHERICAL,
             output_coordinate_system=GEOCENTRIC_SPHERICAL,
             **options):
        return self._eval_reshaped(
            time, location, input_coordinate_system, output_coordinate_system,
            **options
        )

    def _eval_reshaped(self, time, location,
                       input_coordinate_system, output_coordinate_system,
                       f107, imf_v, imf_by, imf_bz, tilt_angle, **options):
        """ Reshape inputs to and output from the pyAMPS compatible dimensions.
        """

        def _broadcast_or_reshape(variable, shape):
            variable = asarray(variable)
            if variable.ndim:
                return variable.reshape(shape)
            return broadcast_to(variable, shape)

        location = asarray(location)
        shape = location.shape

        if not location.size:
            return empty(shape)

        if location.ndim > 1:
            size = prod(shape[:-1])
            location = location.reshape((size, shape[-1]))

            time = _broadcast_or_reshape(time, size)
            f107 = _broadcast_or_reshape(f107, size)
            imf_v = _broadcast_or_reshape(imf_v, size)
            imf_by = _broadcast_or_reshape(imf_by, size)
            imf_bz = _broadcast_or_reshape(imf_bz, size)
            tilt_angle = _broadcast_or_reshape(tilt_angle, size)

        return self._eval(
            time, location, input_coordinate_system, output_coordinate_system,
            f107, imf_v, imf_by, imf_bz, tilt_angle, **options
        ).reshape(shape)

    def _eval(self, time, location,
              input_coordinate_system, output_coordinate_system,
              f107, imf_v, imf_by, imf_bz, tilt_angle, **options):
        """ Evaluate AMPS magnetic field model for the given MJD2000 times and
        coordinates.
        """
        geodetic_coordinates = convert(
            location, input_coordinate_system, GEODETIC_ABOVE_WGS84
        )

        b_e, b_n, b_u = get_B_space( #pylint: disable=unbalanced-tuple-unpacking
            glat=geodetic_coordinates[:, 0],
            glon=geodetic_coordinates[:, 1],
            height=geodetic_coordinates[:, 2],
            time=mjd2000_to_dt64ms(time),
            v=imf_v,
            By=imf_by,
            Bz=imf_bz,
            tilt=tilt_angle,
            f107=f107,
            epoch=float(self._get_epoch(time)),
            h_R=self.REFERENCE_HEIGHT,
            chunksize=self.CHUNK_SIZE,
            coeff_fn=self.filename,
        )

        return vrotate(
            stack((b_n, b_e, b_u), axis=-1),
            geodetic_coordinates,
            location,
            GEODETIC_ABOVE_WGS84,
            output_coordinate_system,
        ) * options.get('scale', 1.0)

    @classmethod
    def _get_epoch(cls, time):
        """ Get decimal year epoch for the given MJD time array. """
        time = asarray(time)
        if time.size:
            return mjd2000_to_decimal_year(0.5*(time.min() + time.max()))
        return cls.DEFAULT_EPOCH
