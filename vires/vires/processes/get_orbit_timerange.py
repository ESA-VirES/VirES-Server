#-------------------------------------------------------------------------------
#
# WPS process converting orbit numbers into time ranges
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=import-error,no-self-use

from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, FormatJSON, CDObject,
)
from vires.time_util import mjd2000_to_datetime
from vires.orbit_counter import get_orbit_timerange
from vires.processes.base import WPSProcess
from vires.cache_util import cache_path
from vires.data.vires_settings import ORBIT_COUNTER_FILE


class GetOrbitTimeRange(WPSProcess):
    """Translate the given range of orbits into the corresponding time-range.
    """
    identifier = "vires:get_orbit_timerange"
    title = "Orbit to time-range translation."
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("spacecraft", LiteralData(
            'spacecraft', str, optional=False,
            abstract="Spacecraft identifier",
            allowed_values=list(ORBIT_COUNTER_FILE),
        )),
        ("start_orbit", LiteralData(
            'start_orbit', int, optional=False,
            abstract="Start orbit number",
            allowed_values=AllowedRange(1, None, dtype=int),
        )),
        ("end_orbit", LiteralData(
            'end_orbit', int, optional=False,
            abstract="End orbit number",
            allowed_values=AllowedRange(1, None, dtype=int),
        )),
    ]

    outputs = [
        ("orbit_timerange", ComplexData(
            "orbit_timerange", title="Time-range of the selected orbits.",
            formats=[FormatJSON()],
        )),
    ]

    def execute(self, spacecraft, start_orbit, end_orbit, **kwargs):
        """ Execute process. """
        if end_orbit < start_orbit:
            start_orbit, end_orbit = end_orbit, start_orbit

        orbit_counter_file = cache_path(ORBIT_COUNTER_FILE[spacecraft])

        start_orbit, end_orbit, start_time, end_time = get_orbit_timerange(
            orbit_counter_file, start_orbit, end_orbit
        )

        output = {
            "spacecraft": spacecraft,
            "start_orbit": start_orbit,
            "end_orbit": end_orbit,
            "start_time": mjd2000_to_datetime(start_time).isoformat("T") + "Z",
            "end_time": mjd2000_to_datetime(end_time).isoformat("T") + "Z",
        }

        return CDObject(output, format=FormatJSON(), **kwargs['orbit_timerange'])
