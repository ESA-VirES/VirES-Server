#-------------------------------------------------------------------------------
#
# Mission specific orbit info setup.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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

from collections import namedtuple
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    ORBIT_COUNTER_FILE, ORBIT_DIRECTION_GEO_FILE, ORBIT_DIRECTION_MAG_FILE,
)
from .time_series import OrbitCounter, OrbitDirection, QDOrbitDirection


OrbitSources = namedtuple(
    "OrbitSources",
    ["orbit_counter", "orbit_direction", "qd_orbit_direction"]
)


def get_orbit_sources(mission, spacecraft, grade):
    """ Construct OrbitCounter, OrbitDirection and QDOrbitDirection time series
    objects for the given mission, spacecraft and grade values.
    """
    try:
        return OrbitSources(
            OrbitCounter(
                ":".join(["OrbitCounter", mission, spacecraft or ""]),
                cache_path(ORBIT_COUNTER_FILE[(mission, spacecraft)])
            ),
            OrbitDirection(
                ":".join(["OrbitDirection", mission, spacecraft or "", grade or ""]),
                cache_path(ORBIT_DIRECTION_GEO_FILE[(mission, spacecraft, grade)])
            ),
            QDOrbitDirection(
                ":".join(["QDOrbitDirection", mission, spacecraft or "", grade or ""]),
                cache_path(ORBIT_DIRECTION_MAG_FILE[(mission, spacecraft, grade)])
            ),
        )
    except KeyError:
        return ()
