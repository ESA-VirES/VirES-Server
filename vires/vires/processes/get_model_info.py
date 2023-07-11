#-------------------------------------------------------------------------------
#
# WPS process fetching information about the provided magnetic models.
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=unused-argument

from io import StringIO
from itertools import chain
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, FormatJSON, CDFileWrapper, CDObject,
)
from eoxserver.services.ows.wps.exceptions import InvalidOutputDefError
from vires.time_util import (
    mjd2000_to_datetime, decimal_year_to_mjd2000, naive_to_utc, format_datetime,
)
from vires.magnetic_models import MODEL_LIST
from vires.processes.base import WPSProcess
from vires.processes.util import parse_model_list


MIN_MJD2000 = decimal_year_to_mjd2000(1.0)
MAX_MJD2000 = decimal_year_to_mjd2000(4000.0)

DEFAULT_MODEL_IDS = ",".join(sorted(MODEL_LIST))


class GetModelInfo(WPSProcess):
    """ Process returning validity intervals of requested models.
    """
    identifier = "vires:get_model_info"
    title = "Fetch merged SWARM products."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("model_ids", LiteralData(
            "model_ids", str, optional=True, default=None,
            title="Model identifiers",
            abstract=(
                "Optional list of the forward Earth magnetic field model "
                "identifiers. All build-in models selected by default."
            ),
        )),
        ("shc", ComplexData(
            "shc",
            title="Custom model coefficients.",
            abstract=(
                "Custom forward magnetic field model coefficients encoded "
                " in the SHC plain-text format."
            ),
            optional=True,
            formats=(FormatText("text/plain"),),
        )),
    ]

    outputs = [
        ("output", ComplexData(
            "output", title="Output data", formats=(
                FormatText("text/csv"),
                FormatJSON("application/json"),
            )
        )),
    ]

    def execute(self, model_ids, shc, output, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)

        # parse inputs
        if model_ids is None:
            model_ids = DEFAULT_MODEL_IDS

        models, _ = parse_model_list("model_ids", model_ids, shc)

        access_logger.info("request: models: (%s), ", model_ids)

        if output["mime_type"] == "text/csv":
            return self._csv_output(models, output)
        if output["mime_type"] == "application/json":
            return self._json_output(models, output)

        raise InvalidOutputDefError(
            "output",
            f"Unexpected output format {output['mime_type']!r} requested!"
        )

    @classmethod
    def _csv_output(cls, models, output):
        output_fobj = StringIO()
        output_fobj.write(
            "modelId,validityStart,validityStop,modelExpression,"
            "sources\r\n"
        )
        for model in sorted(models, key=lambda model: model.name):
            validity_start, validity_stop = model.validity
            output_fobj.write("%s,%s,%s,\"%s\",\"%s\"\r\n" % (
                model.name,
                cls._format_time(validity_start),
                cls._format_time(validity_stop),
                model.expression,
                " ".join(model.sources),
            ))
        return CDFileWrapper(output_fobj, **output)

    @classmethod
    def _json_output(cls, models, output):

        def _get_model_info(model):
            validity_start, validity_stop = model.validity
            return {
                "name": model.name,
                "expression": model.expression,
                "validity": {
                    "start": cls._format_time(validity_start),
                    "end": cls._format_time(validity_stop),
                },
                "sources": model.sources,
            }

        return CDObject([
            _get_model_info(model) for model in models
        ], format=FormatJSON(), **output)

    @staticmethod
    def _format_time(time):
        tobj = mjd2000_to_datetime(max(MIN_MJD2000, min(MAX_MJD2000, time)))
        return format_datetime(naive_to_utc(tobj))
