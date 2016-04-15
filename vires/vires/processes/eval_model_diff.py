#-------------------------------------------------------------------------------
#
# Magnetic models' difference evaluation
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
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
from logging import getLogger, DEBUG
from uuid import uuid4
from datetime import datetime
from numpy import (
    flipud, empty, linspace, meshgrid, amin, amax,
)
from matplotlib import pyplot
from eoxmagmod import (
    GEODETIC_ABOVE_WGS84, vnorm, read_model_shc,
)
from eoxserver.core import Component, implements
from eoxserver.contrib import gdal
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import (
    ExecuteError, InvalidInputValueError,
)
from eoxserver.services.ows.wps.parameters import (
    BoundingBox, BoundingBoxData, ComplexData, CDFile,
    FormatText, FormatBinaryRaw, FormatBinaryBase64,
    LiteralData, AllowedRange
)
from vires.config import SystemConfigReader
from vires.util import get_color_scale, get_model
from vires.time_util import datetime_to_decimal_year, naive_to_utc
from vires.perf_util import ElapsedTimeLogger
from vires.forward_models.base import EVAL_VARIABLE

logger = getLogger("vires.processes.%s" % __name__.split(".")[-1])

class EvalModelDiff(Component):
    """ This process calculates difference of two magnetic models.
    """
    implements(ProcessInterface)

    identifier = "eval_model_diff"
    title = "Evaluate model difference"
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
        ("model1_id", LiteralData(
            "model", str, optional=False,
            title="The model identifier."
            #TODO: list available models.
        )),
        ("model2_id", LiteralData(
            "reference_model", str, optional=False,
            title="The identifier of the second (reference) model."
            #TODO: list available models.
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

    def parse_model(self, model_id, shc, input_id):
        if model_id == "Custom_Model":
            model = read_model_shc(shc)
        else:
            model = get_model(model_id)
            if model is None:
                raise InvalidInputValueError(
                    input_id, "Invalid model identifier %r!" % model_id
                )
        return model

    def execute(self, model1_id, model2_id, shc, variable, begin_time, end_time,
                elevation, range_max, range_min, bbox, width, height,
                style, output, **kwarg):
        # get configurations
        conf_sys = SystemConfigReader()

        # convert bounding box to a simple easting/nothing tuple
        bbox = (bbox[0][1], bbox[0][0], bbox[1][1], bbox[1][0])

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)
        mean_decimal_year = datetime_to_decimal_year(
            (end_time - begin_time)/2 + begin_time
        )

        color_map = get_color_scale(style)

        model1 = self.parse_model(model1_id, shc, "model")
        model2 = self.parse_model(model2_id, shc, "reference_model")

        hd_x = (0.5 / width) * (bbox[2] - bbox[0])
        hd_y = (0.5 / height) * (bbox[1] - bbox[3])
        lons, lats = meshgrid(
            linspace(bbox[0] + hd_x, bbox[2] - hd_x, width, endpoint=True),
            linspace(bbox[3] + hd_y, bbox[1] - hd_y, height, endpoint=True)
        )

        # Geodetic coordinates with elevation above the WGS84 ellipsoid.
        coord_gdt = empty((height, width, 3))
        coord_gdt[:, :, 0] = lats
        coord_gdt[:, :, 1] = lons
        coord_gdt[:, :, 2] = elevation

        with ElapsedTimeLogger("%s.%s %dx%dpx evaluated in" % (
            model1_id, variable, width, height
        ), logger, DEBUG):
            model1_field = model1.eval(
                coord_gdt,
                mean_decimal_year,
                GEODETIC_ABOVE_WGS84,
                GEODETIC_ABOVE_WGS84,
                secvar=False,
                maxdegree=-1,
                mindegree=-1,
                check_validity=False
            )

        with ElapsedTimeLogger("%s.%s %dx%dpx evaluated in" % (
            model2_id, variable, width, height
        ), logger, DEBUG):
            model2_field = model2.eval(
                coord_gdt,
                mean_decimal_year,
                GEODETIC_ABOVE_WGS84,
                GEODETIC_ABOVE_WGS84,
                secvar=False,
                maxdegree=-1,
                mindegree=-1,
                check_validity=False
            )

        # TODO: show also vnorm(model1_field - model2_field)
        pixel_array = (
            EVAL_VARIABLE[variable](model1_field, coord_gdt) -
            EVAL_VARIABLE[variable](model2_field, coord_gdt)
        )

        range_min = amin(pixel_array) if range_min is None else range_min
        range_max = amax(pixel_array) if range_max is None else range_max
        if range_max < range_min:
            range_max, range_min = range_min, range_max
        logger.debug("range: %s", (range_min, range_max))

        # scale pixel values
        scale_factor = 255.0 / (range_max - range_min)
        pixel_array = scale_factor * (pixel_array - range_min)

        # the output image
        temp_basename = uuid4().hex
        temp_filename = join(conf_sys.path_temp, temp_basename + ".png")

        try:
            array_to_colormap_png(temp_filename, pixel_array, color_map)
            #array_to_png(temp_filename, pixel_array)

            result = CDFile(temp_filename, **output)

        except Exception as exc:
            if exists(temp_filename):
                remove(temp_filename)
            raise ExecuteError(exc)

        return {
            "output": result,
            "style_range": "%s,%s,%s"%(style, range_min, range_max),
        }


def array_to_colormap_png(filename, data, color_map):
    """ Convert an array to coloured PNG. """
    fig = pyplot.imshow(flipud(data), vmin=0, vmax=256, origin="lower")
    fig.set_cmap(color_map)
    fig.write_png(filename, True)


def array_to_grayscale_png(filename, data):
    """ Convert an array to PNG """
    height, width = data.shape
    mem_driver = gdal.GetDriverByName('MEM')
    png_driver = gdal.GetDriverByName('PNG')
    mem_ds = mem_driver.Create('', width, height, 1, gdal.GDT_Byte)
    mem_ds.GetRasterBand(1).WriteArray(data)
    png_driver.CreateCopy(filename, mem_ds, 0)