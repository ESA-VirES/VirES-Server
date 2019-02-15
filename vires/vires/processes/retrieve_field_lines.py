#-------------------------------------------------------------------------------
#
# Magnetic model field lines retrieval.
#
# Project: VirES
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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
# pylint: disable=missing-docstring, too-many-arguments, too-many-locals
# pylint: disable=too-few-public-methods, no-self-use

from itertools import izip
from cStringIO import StringIO
from datetime import datetime
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, LogNorm
from numpy import empty, linspace, meshgrid

from eoxmagmod import (
    trace_field_line, GEODETIC_ABOVE_WGS84, GEOCENTRIC_CARTESIAN, vnorm
)
from eoxserver.services.ows.wps.parameters import (
    LiteralData, BoundingBoxData, ComplexData, CDFileWrapper, FormatText,
    AllowedRange,
)
from vires.time_util import datetime_to_mjd2000, naive_to_utc
from vires.perf_util import ElapsedTimeLogger
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_composed_models, parse_style, get_f107_value,
)


class RetrieveFieldLines(WPSProcess):
    """ This process generates a set of field lines passing trough the given
    area of interest.
    """
    identifier = "retrieve_field_lines"
    title = "Generate field lines"
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("model_ids", LiteralData(
            'model_ids', str, optional=False,
            abstract="String input for model identifiers (comma separator)",
        )),
        ("shc", ComplexData(
            'shc',
            title="Custom model coefficients.",
            abstract=(
                "Custom forward magnetic field model coefficients encoded "
                " in the SHC plain-text format."
            ),
            optional=True,
            formats=(FormatText('text/plain'),)
        )),
        ("begin_time", LiteralData(
            'begin_time', datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData(
            'end_time', datetime, optional=False,
            abstract="End of the time interval",
        )),
        ("elevation", LiteralData(
            "elevation", float, optional=True, uoms=(("km", 1.0), ("m", 1e-3)),
            default=0.0, allowed_values=AllowedRange(-1., 1000., dtype=float),
            abstract="Height above WGS84 ellipsoid used to evaluate the model.",
        )),
        ("bbox", BoundingBoxData(
            "bbox", crss=(4326,), optional=False, title="Area of interest",
            abstract="Mandatory area of interest encoded as WPS bounding box.",
        )),
        ("lines_per_col", LiteralData(
            'lines_per_col', int, optional=True, default=4, title="Resolution",
            abstract=(
                "This parameter sets the number of the generated field "
                "lines per northing extent of the bounding box."
            ),
        )),
        ("lines_per_row", LiteralData(
            'lines_per_row', int, optional=True, default=4, title="Resolution",
            abstract=(
                "This parameter sets the number of the generated field "
                "lines per easing extent of the bounding box."
            ),
        )),
        ("log_scale", LiteralData(
            'log_scale', bool, optional=True, default=False,
            abstract="Apply logarithmic scale field line colouring.",
        )),
        ("range_min", LiteralData(
            "range_min", float, optional=True, default=None,
            abstract="Minimum displayed value."
        )),
        ("range_max", LiteralData(
            "range_max", float, optional=True, default=None,
            abstract="Maximum displayed value."
        )),
        ("style", LiteralData(
            'style', str, optional=True, default="jet",
            abstract="Colour-map to be applied to visualization",
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Fields lines",
            abstract="Calculated field lines and coloured field strength.",
            formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def execute(self, model_ids, shc, begin_time, end_time, elevation,
                bbox, lines_per_col, lines_per_row, style, range_min,
                range_max, log_scale, output, **kwarg):
        # parse model and style
        models, _ = parse_composed_models("model_ids", model_ids, shc)
        color_map = parse_style("style", style)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)
        mean_time = 0.5 * (
            datetime_to_mjd2000(end_time) + datetime_to_mjd2000(begin_time)
        )

        self.access_logger.info(
            "request: toi: (%s, %s), aoi: %s, elevation: %g, "
            "models: (%s), grid: (%d, %d)",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            bbox[0]+bbox[1] if bbox else (-90, -180, 90, 180), elevation,
            ", ".join(
                "%s = %s" % (model.name, model.full_expression)
                for model in models
            ),
            lines_per_col, lines_per_row,
        )

        # parse range bounds
        self.logger.debug(
            "output %s data range: %s",
            "logarithmic" if log_scale else "linear",
            (range_min, range_max)
        )

        def generate_field_lines():
            n_lines = lines_per_row * lines_per_col
            coord_gdt = empty((lines_per_col, lines_per_row, 3))
            coord_gdt[..., 1], coord_gdt[..., 0] = meshgrid(
                linspace(bbox.lower[1], bbox.upper[1], lines_per_row),
                linspace(bbox.lower[0], bbox.upper[0], lines_per_col)
            )
            coord_gdt[..., 2] = elevation

            total_count = 0
            for model in models:
                model_count = 0

                options = {}
                if "f107" in model.model.parameters:
                    options["f107"] = get_f107_value(mean_time)

                self.logger.debug("%s model options: %s", model.name, options)

                for point in coord_gdt.reshape((n_lines, 3)):
                    # get field-line coordinates and field vectors
                    with ElapsedTimeLogger(
                        "%s field line " % model.name, self.logger
                    ) as etl:
                        line_coords, line_field = trace_field_line(
                            model.model, mean_time, point,
                            GEODETIC_ABOVE_WGS84, GEOCENTRIC_CARTESIAN,
                            model_options=options,
                        )
                        etl.message += (
                            "with %d points integrated in" % len(line_coords)
                        )
                    # convert coordinates from kilometres to metres
                    yield model.name, 1e3*line_coords, vnorm(line_field)
                    model_count += line_coords.shape[0]

                self.access_logger.info(
                    "model: %s, lines: %d, points: %d",
                    model.name, n_lines, model_count,
                )
                total_count += model_count

            self.access_logger.info(
                "response: lines: %d, points: %d, mime-type: %s",
                n_lines * len(models), total_count, output['mime_type'],
            )

        # data colouring
        norm = LogNorm if log_scale else Normalize
        color_scale = ScalarMappable(norm(range_min, range_max), color_map)

        # CSV text output
        output_fobj = StringIO()
        output_fobj.write('id,color_r,color_g,color_b,pos_x,pos_y,pos_z\r\n')
        for idx, (model, coords, values) in enumerate(generate_field_lines()):
            format_str = (
                ("%s-%d" % (model, idx + 1)) + ",%d,%d,%d,%.0f,%.0f,%.0f\r\n"
            )
            colors = color_scale.to_rgba(values, bytes=True)
            for (x__, y__, z__), (red, green, blue, _) in izip(coords, colors):
                output_fobj.write(
                    format_str % (red, green, blue, x__, y__, z__)
                )

        return CDFileWrapper(output_fobj, **output)
