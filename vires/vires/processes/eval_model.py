#-------------------------------------------------------------------------------
#
# Magnetic model evaluation
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments,too-many-locals
# pylint: disable=unused-argument,no-self-use,too-few-public-methods

from datetime import datetime
from eoxserver.services.ows.wps.parameters import (
    BoundingBox, BoundingBoxData, ComplexData,
    FormatText, FormatBinaryRaw, FormatBinaryBase64,
    LiteralData, AllowedRange
)
from vires.time_util import datetime_to_mjd2000, mjd2000_to_datetime, naive_to_utc
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_model_expression, parse_style,
    render_model, ALLOWED_VARIABLES,
)


class EvalModel(WPSProcess):
    """ This process calculates difference of two magnetic models.
    """
    identifier = "eval_model"
    title = "Evaluate model"
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("bbox", BoundingBoxData(
            "bbox", crss=(4326,), optional=True, title="Area of interest",
            abstract="Optional area of interest encoded ",
            default=BoundingBox(((-90., -180.), (+90., +180.))),
        )),
        ("width", LiteralData(
            "width", int, optional=False, title="Image width in pixels.",
            allowed_values=AllowedRange(1, 1024, dtype=int), default=256,
        )),
        ("height", LiteralData(
            "height", int, optional=False, title="Image height in pixels.",
            allowed_values=AllowedRange(1, 1024, dtype=int), default=128,
        )),
        ("begin_time", LiteralData(
            "begin_time", datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData(
            "end_time", datetime, optional=False,
            abstract="End of the time interval",
        )),
        ("model_expression", LiteralData(
            "model", str, optional=False,
            title="Model expression."
        )),
        ("variable", LiteralData(
            "variable", str, optional=True, default="F",
            abstract="Variable to be evaluated.",
            allowed_values=tuple(ALLOWED_VARIABLES),
        )),
        ("elevation", LiteralData(
            "elevation", float, optional=True, uoms=(("km", 1.0), ("m", 1e-3)),
            default=0.0, allowed_values=AllowedRange(-1., 1000., dtype=float),
            abstract="Height above WGS84 ellipsoid used to evaluate the model.",
        )),
        ("range_min", LiteralData(
            "range_min", float, optional=True, default=None,
            abstract="Minimum displayed value."
        )),
        ("range_max", LiteralData(
            "range_max", float, optional=True, default=None,
            abstract="Maximum displayed value."
        )),
        ("shc", ComplexData(
            "shc", title="SHC file data", optional=True,
            formats=(FormatText("text/plain"),),
            abstract="The custom model coefficients encoded in the SHC format.",
        )),
        ("style", LiteralData(
            "style", str, optional=True, default="jet",
            abstract="The name of the colour-map applied to the result.",
            #TODO: list available colour-maps.
        )),
    ]

    outputs = [
        ("output", ComplexData(
            "output", title="The output image.", formats=(
                FormatBinaryBase64("image/png"),
                FormatBinaryRaw("image/png"),
            )
        )),
        ("style_range", LiteralData(
            "style_range", str, title="Style and value range.",
            abstract="Colour-map name and range of values of the result."
        )),
    ]

    def execute(self, model_expression, shc, variable, begin_time, end_time,
                elevation, range_max, range_min, bbox, width, height,
                style, output, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)

        # parse models and styles
        color_map = parse_style("style", style)
        model, _ = parse_model_expression("model", model_expression, shc)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)
        mean_time = 0.5 * (
            datetime_to_mjd2000(end_time) + datetime_to_mjd2000(begin_time)
        )

        access_logger.info(
            "request: time: %s, aoi: %s, elevation: %g, "
            "model: %s, variable: %s, image-size: (%d, %d), mime-type: %s",
            naive_to_utc(mjd2000_to_datetime(mean_time)).isoformat("T"),
            bbox[0] + bbox[1], elevation, model.full_expression,
            variable, width, height, output['mime_type'],
        )

        (y_min, x_min), (y_max, x_max) = bbox

        result, _, (range_min, range_max) = render_model(
            model=model,
            variable=variable,
            mjd2000=mean_time,
            srid=4326,
            bbox=(x_min, y_min, x_max, y_max),
            elevation=elevation,
            size=(width, height),
            value_range=(range_min, range_max),
            colormap=color_map,
            response_format=output['mime_type'],
            is_transparent=True,
            grid_step=(1, 1), # no interpolation
            wps_output_def=output,
        )

        return {
            "output": result,
            "style_range": "%s,%s,%s"%(style, range_min, range_max),
        }
