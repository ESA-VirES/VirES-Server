#-------------------------------------------------------------------------------
#
# Orbit direction file handling.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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

from os.path import exists
from numpy import array, nan

from .util import full
from .cdf_util import (
    cdf_open, cdf_time_subset, cdf_time_interp, datetime_to_cdf_rawtime,
    CDF_EPOCH_TYPE,
)

TYPES = {"OrbitDirection": "int8", "BoundaryType": "int8"}
NODATA = {"OrbitDirection": 0, "BoundaryType": -1}
FIELDS_ALL = ("Timestamp", "OrbitDirection", "BoundaryType")
FIELD_TIME = FIELDS_ALL[0]
FIELDS_DATA = FIELDS_ALL[1:]


def fetch_orbit_direction_data(filename, start, stop, fields=FIELDS_ALL):
    """ Extract non-interpolated orbit direction data. """
    def _from_datetime(time):
        return datetime_to_cdf_rawtime(time, CDF_EPOCH_TYPE)

    if not exists(filename):
        return dict((field, array([])) for field in fields)

    with cdf_open(filename) as cdf:
        return dict(cdf_time_subset(
            cdf, _from_datetime(start), _from_datetime(stop),
            fields=fields, margin=1, time_field=FIELD_TIME,
        ))


def interpolate_orbit_direction_data(filename, time, nodata=None,
                                     fields=FIELDS_DATA, kind='zero'):
    """ Interpolate orbit direction data.
    All variables are interpolated using the lower nearest neighbour
    interpolation.
    """
    # fill the default no-data type
    _nodata = dict(NODATA)
    if nodata:
        _nodata.update(nodata)
    nodata = _nodata

    if exists(filename):
        with cdf_open(filename) as cdf:
            return dict(
                cdf_time_interp(
                    cdf, time, fields, types=TYPES, nodata=nodata,
                    time_field=FIELD_TIME, kind=kind
                )
            )
    else:
        return dict(
            (field, full(time.shape, nodata.get(field, nan), types.get(field)))
            for field in fields
        )
