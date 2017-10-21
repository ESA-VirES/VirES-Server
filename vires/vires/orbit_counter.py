#-------------------------------------------------------------------------------
#
# Orbit number file handling.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from os.path import exists
from numpy import loadtxt, array, nan

from .util import full
from .cdf_util import cdf_open, cdf_time_subset, cdf_time_interp
from .time_util import datetime_to_mjd2000


def parse_orbit_counter_file(src_file):
    """ Parse Swarm orbit counter text file. """
    data = loadtxt(
        src_file,
        skiprows=1,
        converters={2: (lambda v: 0), 3: (lambda v: 0)}
    )
    return (
        data[:, 0].astype('uint32'), data[:, 1], data[:, 4],
        data[:, 5].astype('uint8')
    )


def update_orbit_counter_file(src_file, dst_file):
    """ Update Swarm orbit counter text file. """
    with cdf_open(dst_file, "w") as cdf:
        cdf["orbit"], cdf["MJD2000"], cdf["phi_AN"], cdf["Source"] = (
            parse_orbit_counter_file(src_file)
        )


def fetch_orbit_counter_data(filename, start, stop,
                             fields=("MJD2000", "orbit", "phi_AN", "Source")):
    """ Extract non-interpolated orbit counter data. """
    if not exists(filename):
        return dict((field, array([])) for field in fields)

    with cdf_open(filename) as cdf:
        return dict(cdf_time_subset(
            cdf, datetime_to_mjd2000(start), datetime_to_mjd2000(stop),
            fields=fields, margin=1, time_field="MJD2000",
        ))


def interpolate_orbit_counter_data(filename, time, nodata=None,
                                   fields=("orbit", "phi_AN", "Source"),
                                   kind='zero'):
    """ Interpolate orbit counter data.
    All variables are interpolated using the lower nearest neighbour
    interpolation.
    """
    types = {"orbit": "int32", "Source": "int8"}

    # fill the default no-data type
    _nodata = {"orbit": -1, "Source": -1}
    if nodata:
        _nodata.update(nodata)
    nodata = _nodata

    if exists(filename):
        with cdf_open(filename) as cdf:
            return dict(
                cdf_time_interp(
                    cdf, time, fields, types=types, nodata=nodata,
                    time_field="MJD2000", kind=kind
                )
            )
    else:
        return dict(
            (field, full(time.shape, nodata.get(field, nan), types.get(field)))
            for field in fields
        )
