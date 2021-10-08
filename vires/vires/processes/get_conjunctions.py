#------------------------------------------------------------------------------
#
# WPS process fetching list spacecraft conjunctions
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=no-self-use,unused-argument,too-many-arguments,too-many-locals

from io import StringIO, BytesIO
from os import remove
from os.path import join, exists
from uuid import uuid4
from datetime import datetime
import msgpack
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, FormatBinaryRaw,
    CDTextBuffer, CDObject, CDFileWrapper, CDFile, AllowedRange,
)
from eoxserver.services.ows.wps.exceptions import (
    InvalidInputValueError, InvalidOutputDefError,
)
from vires.config import SystemConfigReader
from vires.cdf_util import cdf_open
from vires.cdf_write_util import cdf_add_variable
from vires.time_util import (
    format_datetime, datetime64_to_unix_epoch,
)
from vires.cache_util import cache_path
from vires.processes.base import WPSProcess
from vires.data.vires_settings import ORBIT_CONJUNCTION_FILE, DEFAULT_MISSION
from vires.conjunctions.reader import read_conjunctions


_MISSION_SPACECRAFT_PAIRS = {
    item for pair in ORBIT_CONJUNCTION_FILE for item in pair
}

MISSIONS = sorted({mission for mission, _ in _MISSION_SPACECRAFT_PAIRS})
SPACECRAFTS = sorted({spacecraft for _, spacecraft in _MISSION_SPACECRAFT_PAIRS})

MISSION_SPACECRAFTS = {
    mission: sorted([
        spacecraft for key, spacecraft in _MISSION_SPACECRAFT_PAIRS
        if key == mission and spacecraft
    ])
    for mission in MISSIONS
}

class GetConjunctions(WPSProcess):
    """ Process for retrieving spacecraft conjunctions.
    """
    identifier = "vires:get_conjunctions"
    title = "Get list of spacecraft conjunctions"
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("mission1", LiteralData(
            "mission1", str, optional=True, default=DEFAULT_MISSION,
            abstract="Primary mission identifier",
            allowed_values=MISSIONS,
        )),
        ("spacecraft1", LiteralData(
            "spacecraft1", str, optional=True,
            abstract="Primary spacecraft identifier",
            allowed_values=SPACECRAFTS,
        )),
        ("mission2", LiteralData(
            "mission2", str, optional=True, default=DEFAULT_MISSION,
            abstract="Secondary mission identifier",
            allowed_values=MISSIONS,
        )),
        ("spacecraft2", LiteralData(
            "spacecraft2", str, optional=True,
            abstract="Secondary spacecraft identifier",
            allowed_values=SPACECRAFTS,
        )),
        ("begin_time", LiteralData(
            "begin_time", datetime, optional=True, title="Begin time",
            abstract="Start of the selection time interval",
        )),
        ("end_time", LiteralData(
            "end_time", datetime, optional=True, title="End time",
            abstract="End of the selection time interval",
        )),
        ("max_angular_separation", LiteralData(
            "angular_separation_threshold", float, optional=True, default=1.0,
            allowed_values=AllowedRange(0.0, 180.0, dtype=float),
            title="Maximum allowed angular separation.",
            abstract=(
                "Maximum allowed angular separation (great-circle distance) "
                " between the spacecrafts of the selected conjunctions."
            ),
        )),
    ]

    outputs = [
        ("output", ComplexData(
            "output", title="Output data", formats=(
                FormatText("text/csv"),
                FormatBinaryRaw("application/msgpack"),
                FormatBinaryRaw("application/x-msgpack"),
                FormatBinaryRaw("application/cdf"),
                FormatBinaryRaw("application/x-cdf"),
            )
        )),
        ("source_products", ComplexData(
            "source_products", title="List of source products.", formats=(
                FormatText("text/plain"),
            )
        )),
    ]

    @staticmethod
    def _checkspacecraft(mission, spacecraft, parameter):
        error = None
        if MISSION_SPACECRAFTS[mission]:
            if not spacecraft:
                error = (
                    f"Missing mandatory {mission} spacecraft identifier. "
                    f"Possible values are: {','.join(MISSION_SPACECRAFTS[mission])}"
                )
            elif spacecraft not in MISSION_SPACECRAFTS[mission]:
                error = (
                    f"Invalid {mission} spacecraft identifier {spacecraft}. "
                    f"Possible values are: {','.join(MISSION_SPACECRAFTS[mission])}"
                )
        elif spacecraft:
            error = f"No spacecraft identifier allowed for the {mission} mission!"

        if error:
            raise InvalidInputValueError(parameter, error)


    def execute(self, mission1, spacecraft1, mission2, spacecraft2,
                begin_time, end_time, max_angular_separation, output,
                source_products, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        spacecraft1 = spacecraft1 or None
        spacecraft2 = spacecraft2 or None

        self._checkspacecraft(mission1, spacecraft1, "spacecraft1")
        self._checkspacecraft(mission2, spacecraft2, "spacecraft2")

        if (mission1, spacecraft1) == (mission2, spacecraft2):
            raise InvalidInputValueError("spacecraft2", (
                "Primary and secondary spacecrafts must differ."
            ))

        pair_selection = tuple(sorted([
            (mission1, spacecraft1), (mission2, spacecraft2)
        ]))

        try:
            conjunctions_file = ORBIT_CONJUNCTION_FILE[pair_selection]
        except KeyError:
            raise InvalidInputValueError("spacecraft2", (
                " No conjunction table available for the requested spacecrafts."
            )) from None

        spacecraft_ids = [_format_spacecraft(*item) for item in pair_selection]

        access_logger = self.get_access_logger(**kwargs)
        access_logger.info(
            "request: toi: "
            f"{format_datetime(begin_time) or '-'}/"
            f"{format_datetime(end_time) or '-'}, "
            "spacecrafts: "
            f"{spacecraft_ids[0]}/{spacecraft_ids[1]} "
            f"threshold: {max_angular_separation} "
            f"format: {output['mime_type']}"
        )

        dataset, sources, begin_time, end_time = read_conjunctions(
            cache_path(conjunctions_file), begin_time, end_time,
            max_angular_separation,
        )

        access_logger.info(
            f"response: {len(dataset)} conjunctions extracted "
            f"from {len(sources)} source products."
        )

        basename = (
            f"conjunctions_{spacecraft_ids[0]}_{spacecraft_ids[1]}_"
            f"{begin_time:%Y%m%dT%H%M%S}_"
            f"{end_time:%Y%m%dT%H%M%S}_"
            f"{datetime.utcnow():%Y%m%dT%H%M%S}"
        )

        if output["mime_type"] == "text/csv":
            result = _pack_csv(basename, dataset, sources, **output)

        elif output["mime_type"] in ("application/msgpack", "application/x-msgpack"):
            result = _pack_msgpack(
                basename, dataset, sources, spacecraft_ids,
                begin_time, end_time, max_angular_separation, **output
            )

        elif output["mime_type"] in ("application/cdf", "application/x-cdf"):
            result = _pack_cdf(
                basename, dataset, sources, spacecraft_ids,
                begin_time, end_time, max_angular_separation, **output
            )

        else:
            raise InvalidOutputDefError(
                "output",
                "Unexpected output format %r requested!" % output["mime_type"]
            )

        return {
            "output": result,
            "source_products": CDTextBuffer(
                "\r\n".join(sources + [""]),
                filename=basename+".sources.txt",
                **source_products
            ),
        }


def _pack_cdf(basename, dataset, sources, spacecrafts,
              begin_time, end_time, max_angular_separation, **output):

    temp_filename = None
    if not temp_filename or exists(temp_filename):
        temp_filename = join(
            SystemConfigReader().path_temp,
            f"conjunctions_{uuid4().hex}.cdf"
        )

    if exists(temp_filename):
        remove(temp_filename)

    with cdf_open(temp_filename, 'w') as cdf:
        for variable in ('Timestamp', 'AngularSeparation'):
            cdf_add_variable(
                cdf, variable, dataset[variable],
                dataset.cdf_attr.get(variable, {}),
            )

        # add the global attributes
        cdf.attrs.update({
            "TITLE": basename,
            "DATA_TIMESPAN": ("%s/%s" % (
                format_datetime(begin_time), format_datetime(end_time),
            )),#.replace("+00:00", "Z"),
            "SPACECRAFTS": spacecrafts,
            "MAX_ANGULAR_SEPARATION": max_angular_separation,
            "ORIGINAL_PRODUCT_NAMES": sources,
        })

    return CDFile(temp_filename, filename=basename+".cdf", **output)


def _pack_msgpack(basename, dataset, sources, spacecrafts,
                  begin_time, end_time, max_angular_separation, **output):
    payload = {
        "Timestamp": datetime64_to_unix_epoch(dataset["Timestamp"]).tolist(),
        "AngularSeparation": dataset["AngularSeparation"].tolist(),
        "__info__": {
            "begin_time": format_datetime(begin_time),
            "end_time": format_datetime(end_time),
            "sources": sources,
            "spacecrafts": spacecrafts,
            "max_angular_separation": max_angular_separation,
        }
    }
    return CDObject(
        BytesIO(msgpack.dumps(payload)), filename=basename+".mp", **output
    )


def _pack_csv(basename, dataset, sources, **output):
    variables = ('Timestamp', 'AngularSeparation')
    format_ = "%sZ,%.3f"

    output_fobj = StringIO(newline="\r\n")

    print("%s,%s" % variables, file=output_fobj)
    for record in zip(*[dataset[variable] for variable in variables]):
        print(format_ % record, file=output_fobj)

    return CDFileWrapper(output_fobj, filename=basename+".csv", **output)


def _format_spacecraft(mission, spacecraft):
    return "%s-%s" % (mission, spacecraft) if spacecraft else mission
