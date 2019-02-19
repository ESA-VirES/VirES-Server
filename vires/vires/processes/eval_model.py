#-------------------------------------------------------------------------------
#
# Magnetic model evaluation
#
# Project: VirES
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=missing-docstring,too-many-arguments,too-many-locals
# pylint: disable=unused-argument,no-self-use,too-few-public-methods

from os import remove
from os.path import join, exists
from uuid import uuid4
from datetime import datetime
from matplotlib.colors import Normalize
from numpy import empty, linspace, meshgrid, amin, amax
from eoxmagmod import GEODETIC_ABOVE_WGS84
from eoxserver.services.ows.wps.parameters import (
    BoundingBox, BoundingBoxData, ComplexData, CDFile,
    FormatText, FormatBinaryRaw, FormatBinaryBase64,
    LiteralData, AllowedRange
)
from vires.config import SystemConfigReader
from vires.time_util import datetime_to_mjd2000, naive_to_utc
from vires.perf_util import ElapsedTimeLogger
from vires.ows.wms.model_renderer import EVAL_VARIABLE
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_model_expression, parse_style, data_to_png, get_f107_value,
)


class EvalModel(WPSProcess):
    """ This process calculates difference of two magnetic models.
    """
    identifier = "eval_model"
    title = "Evaluate model"
    metadata = {}
    profiles = ["vires"]

    inputs = [
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
            allowed_values=tuple(EVAL_VARIABLE.keys()),
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
                style, output, **kwarg):
        # get configurations
        conf_sys = SystemConfigReader()

        # parse models and styles
        color_map = parse_style("style", style)
        model, _ = parse_model_expression("model", model_expression, shc)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)
        mean_time = 0.5 * (
            datetime_to_mjd2000(end_time) + datetime_to_mjd2000(begin_time)
        )

        self.access_logger.info(
            "request: toi: (%s, %s), aoi: %s, elevation: %g, "
            "model: %s, variable: %s, image-size: (%d, %d), mime-type: %s",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            bbox[0] + bbox[1], elevation, model.full_expression,
            variable, width, height, output['mime_type'],
        )

        (y_min, x_min), (y_max, x_max) = bbox
        hd_x = (0.5 / width) * (x_max - x_min)
        hd_y = (0.5 / height) * (y_min - y_max)
        lons, lats = meshgrid(
            linspace(x_min + hd_x, x_max - hd_x, width, endpoint=True),
            linspace(y_max + hd_y, y_min - hd_y, height, endpoint=True)
        )

        # Geodetic coordinates with elevation above the WGS84 ellipsoid.
        coord_gdt = empty((height, width, 3))
        coord_gdt[:, :, 0] = lats
        coord_gdt[:, :, 1] = lons
        coord_gdt[:, :, 2] = elevation

        options = {}
        if "f107" in model.model.parameters:
            options["f107"] = get_f107_value(mean_time)

        self.logger.debug("model options: %s", options)

        with ElapsedTimeLogger("%s:%s %dx%dpx %s evaluated in" % (
            model.full_expression, variable, width, height, bbox[0] + bbox[1],
        ), self.logger):
            model_field = model.model.eval(
                mean_time, coord_gdt,
                GEODETIC_ABOVE_WGS84, GEODETIC_ABOVE_WGS84,
                scale=[1, 1, -1], **options
            )

        pixel_array = EVAL_VARIABLE[variable](model_field, coord_gdt)

        range_min = amin(pixel_array) if range_min is None else range_min
        range_max = amax(pixel_array) if range_max is None else range_max
        if range_max < range_min:
            range_max, range_min = range_min, range_max
        self.logger.debug("output data range: %s", (range_min, range_max))
        data_norm = Normalize(range_min, range_max)

        # the output image
        temp_basename = uuid4().hex
        temp_filename = join(conf_sys.path_temp, temp_basename + ".png")

        try:
            data_to_png(temp_filename, pixel_array, data_norm, color_map)
            result = CDFile(temp_filename, **output)
        except Exception:
            if exists(temp_filename):
                remove(temp_filename)
            raise

        return {
            "output": result,
            "style_range": "%s,%s,%s"%(style, range_min, range_max),
        }
