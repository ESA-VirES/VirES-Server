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

from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, FormatJSON, CDObject,
)
from vires.time_util import mjd2000_to_datetime
from vires.orbit_counter import get_orbit_timerange
from vires.processes.base import WPSProcess
from vires.cache_util import cache_path
from vires.time_util import format_datetime, naive_to_utc
from vires.data.vires_settings import ORBIT_COUNTER_FILE, SWARM_MISSION

MISSIONS = sorted(set(mission for mission, _ in ORBIT_COUNTER_FILE))
SPACECRAFTS = sorted(set(
    spacecraft for _, spacecraft in ORBIT_COUNTER_FILE if spacecraft
))

MISSION_SPACECRAFTS = {
    mission: sorted([
        spacecraft for key, spacecraft in ORBIT_COUNTER_FILE
        if key == mission and spacecraft
    ])
    for mission in MISSIONS
}


class GetOrbitTimeRange(WPSProcess):
    """Translate the given range of orbits into the corresponding time-range.
    """
    identifier = "vires:get_orbit_timerange"
    title = "Orbit to time-range translation."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("mission", LiteralData(
            'mission', str, optional=True, default=SWARM_MISSION,
            abstract="Mission identifier",
            allowed_values=MISSIONS,
        )),
        ("spacecraft", LiteralData(
            'spacecraft', str, optional=True,
            abstract="Spacecraft identifier",
            allowed_values=SPACECRAFTS,
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

    def execute(self, mission, spacecraft, start_orbit, end_orbit, **kwargs):
        """ Execute process. """

        try:
            orbit_counter_file = ORBIT_COUNTER_FILE[(mission, spacecraft or None)]
        except KeyError:
            raise InvalidInputValueError("spacecraft", (
                (
                    f"Invalid {mission} spacecraft identifier {spacecraft}. Possible values are: "
                    f"{','.join(MISSION_SPACECRAFTS[mission])}"
                    if spacecraft else
                    f"Missing mandatory {mission} spacecraft identifier. Possible values are: "
                    f"{','.join(MISSION_SPACECRAFTS[mission])}"
                )
                if MISSION_SPACECRAFTS[mission] else
                f"There is no spacecraft identifier allowed for the {mission} "
                "mission!"
            )) from None

        if end_orbit < start_orbit:
            start_orbit, end_orbit = end_orbit, start_orbit

        access_logger = self.get_access_logger(**kwargs)
        access_logger.info(
            "request: mission: %s, spacecraft: %s, start_orbit: %s, end_orbit %s",
            mission, spacecraft or '-', start_orbit, end_orbit,
        )

        start_orbit, end_orbit, start_time, end_time = get_orbit_timerange(
            cache_path(orbit_counter_file), start_orbit, end_orbit
        )

        output = {
            "mission": mission,
            "spacecraft": spacecraft or None,
            "start_orbit": start_orbit,
            "end_orbit": end_orbit,
            "start_time": format_datetime(naive_to_utc(mjd2000_to_datetime(start_time))),
            "end_time": format_datetime(naive_to_utc(mjd2000_to_datetime(end_time))),
        }

        return CDObject(output, format=FormatJSON(), **kwargs['orbit_timerange'])
