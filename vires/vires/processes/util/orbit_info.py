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

from logging import getLogger
from collections import namedtuple
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    ORBIT_COUNTER_FILE, ORBIT_DIRECTION_GEO_FILE, ORBIT_DIRECTION_MAG_FILE,
)
from .time_series import OrbitCounter, OrbitDirection, QDOrbitDirection


def get_orbit_sources(mission, spacecraft, grade):
    """ Construct OrbitCounter, OrbitDirection and QDOrbitDirection time series
    objects for the given mission, spacecraft and grade values.
    """
    return [
        *_yield_orbit_number_source(mission, spacecraft),
        *_yield_orbit_direction_sources(mission, spacecraft, grade),
    ]


def _yield_orbit_number_source(mission, spacecraft):
    try:
        orbit_counter_path = cache_path(ORBIT_COUNTER_FILE[mission, spacecraft])
    except KeyError:
        getLogger(__name__).warning(
            "Orbit counter file not found for mission/spacecraft %s/%s!",
            mission, spacecraft or "<none>"
        )
    else:
        yield OrbitCounter(
            _format_label("OrbitCounter", mission, spacecraft),
            orbit_counter_path
        )


def _yield_orbit_direction_sources(mission, spacecraft, grades):
    od_tables_list = []
    for grade in (grades or "").split("+"):
        grade = grade or None
        try:
            od_tables_list.append(_ODTables(
                grade or None,
                cache_path(ORBIT_DIRECTION_GEO_FILE[(mission, spacecraft, grade)]),
                cache_path(ORBIT_DIRECTION_MAG_FILE[(mission, spacecraft, grade)]),
            ))
        except KeyError:
            getLogger(__name__).warning(
                "Orbit direction tables not found for mission/spacecraft/grade %s/%s/%s!",
                mission, spacecraft or "<none>", grade or "<none>"
            )

    # FIXME: implement proper orbit direction lookup for mixed grades
    #        currently the first found grade is yielded
    for od_tables in od_tables_list:
        yield OrbitDirection(
            _format_label("OrbitDirection", mission, spacecraft, od_tables.grade),
            od_tables.geo_table_path,
        )
        yield QDOrbitDirection(
            _format_label("QDOrbitDirection", mission, spacecraft, od_tables.grade),
            od_tables.mag_table_path,
        )


_ODTables = namedtuple("_ODTables", ["grade", "geo_table_path", "mag_table_path"])


def _format_label(label, *args):
    return ":".join([label, *(arg or "" for arg in args)])
