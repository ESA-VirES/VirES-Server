#-------------------------------------------------------------------------------
#
# Evaluation of magnetic models at user provided times and locations
# - model calculation
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

from numpy import empty
from eoxmagmod import GEOCENTRIC_SPHERICAL, GEOCENTRIC_SPHERICAL
from .common import (
    FORMAT_SPECIFIC_TIME_FORMAT,
    TIME_KEY,
    MJD2000_KEY,
    LOCATION_KEYS,
)


def calculate_model_values(data, models, source_models,
                           get_extra_model_parameters,
                           time_key=MJD2000_KEY, location_keys=LOCATION_KEYS):
    """ Calculate model values. """
    del source_models # FIXME: optimize to prevent repeated calculation

    # NOTE: assuming compatible dimensions
    shape = data[location_keys[0]].shape
    if (
        shape != data[location_keys[1]].shape or
        shape != data[location_keys[2]].shape or
        shape != data[time_key].shape
    ):
        raise ValueError("Data dimension mismatch!")

    # Geocentric spherical coordinates
    coords = empty(shape + (3,))
    coords[..., 0] = data[location_keys[0]] # Latitude degrees
    coords[..., 1] = data[location_keys[1]] # Longitude degrees
    coords[..., 2] = data[location_keys[2]] * 1e-3 # Radius m => km
    mjd2000 = data[time_key] # Timestamp MJD2000

    for model in models:
        model_key = f"B_NEC_{model.name}"
        data[model_key] = model.model.eval(
            mjd2000, coords, GEOCENTRIC_SPHERICAL, GEOCENTRIC_SPHERICAL,
            scale=[1, 1, -1],
            **get_extra_model_parameters(mjd2000, model.model.parameters)
        )

    return data
