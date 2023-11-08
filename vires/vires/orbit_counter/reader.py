#-------------------------------------------------------------------------------
#
# Orbit counter file reader
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

from os.path import exists
from ..cdf_util import cdf_open
from ..aux_common import SingleSourceMixIn, MJD2000TimeMixIn, BaseReader


class OrbitCounterReader(SingleSourceMixIn, MJD2000TimeMixIn, BaseReader):
    """ Orbit counter data reader class. """
    TIME_FIELD = "MJD2000"
    DATA_FIELDS = ("orbit", "phi_AN", "Source")
    TYPES = {"orbit": "int32", "Source": "int8"}
    NODATA = {"orbit": -1, "Source": -1}
    INTERPOLATION_KIND = "zero"


def get_orbit_timerange(filename, start_orbit, end_orbit):
    """ Get ascending node times for the given range of orbit numbers. """
    if not exists(filename):
        raise IOError("File %s does not exist!" % filename)

    def _get_ascending_node_time(orbit_number):
        orbit_number = min(orbits[-1], max(1, orbit_number))
        if orbit_number < 1 or orbit_number > orbits[-1]:
            raise ValueError("Invalid orbit number!")
        assert orbits[orbit_number - 1] == orbit_number
        return orbit_number, times[orbit_number - 1]

    with cdf_open(filename) as cdf:
        orbits = cdf["orbit"][...]
        times = cdf["MJD2000"][...]
        start_orbit, start_time = _get_ascending_node_time(start_orbit)
        end_orbit, end_time = _get_ascending_node_time(end_orbit + 1)
        end_orbit -= 1
        return start_orbit, end_orbit, start_time, end_time


def get_max_orbit_number(filename):
    """ Get maximum orbit number. """
    if not exists(filename):
        raise IOError("File %s does not exist!" % filename)

    with cdf_open(filename) as cdf:
        return cdf["orbit"][-1] - 1
