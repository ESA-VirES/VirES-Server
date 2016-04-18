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

from logging import getLogger, DEBUG
from itertools import izip
from cStringIO import StringIO
from datetime import datetime
from numpy import empty, linspace, meshgrid

from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, LogNorm

from eoxmagmod import GEODETIC_ABOVE_WGS84, GEOCENTRIC_CARTESIAN, vnorm
from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.parameters import (
    LiteralData, BoundingBoxData, ComplexData, CDFileWrapper, FormatText,
)
from vires.time_util import (
    datetime_to_decimal_year, naive_to_utc, datetime_mean,
)
from vires.perf_util import ElapsedTimeLogger
from vires.processes.util import parse_models, parse_style

logger = getLogger("vires.processes.%s" % __name__.split(".")[-1])

class RetrieveFieldLines(Component):
    """ This process generates a set of field lines passing trough the given
    area of interest.
    """
    implements(ProcessInterface)

    identifier = "retrieve_field_lines"
    title = "Generate field lines"
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("bbox", BoundingBoxData(
            "bbox", crss=(4326,), optional=False, title="Area of interest",
            abstract="Mandatory area of interest encoded as WPS bounding box.",
        )),
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
        ("log_scale", LiteralData(
            'logarithmic', bool, optional=True, default=False,
            abstract="Apply logarithmic scale field line colouring.",
        )),
        ("resolution", LiteralData(
            'resolution', int, optional=True, default=4, title="Resolution",
            abstract=(
                "This parameter sets the number of the generated field "
                "lines per each bounding-box dimension."
            ),
        )),
        ("style", LiteralData(
            'style', str, optional=True, default="jet",
            abstract="Colour-map to be applied to visualization",
        )),
        # TODO: range_min, range_max
        ("dim_range", LiteralData(
            'dim_range', str, optional=True, default="30000,60000",
            abstract="Range dimension for visualized parameter",
        )),
        # TODO: Remove the colors parameter from the client.
        ("colors", LiteralData(
            'colors', str, optional=True, default="30000,60000",
            abstract="Not used.",
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Fields lines",
            abstract="Calculated field lines and coloured field strength.",
            formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def execute(self, model_ids, shc, begin_time, end_time, bbox, log_scale,
                resolution, style, dim_range, output, **kwarg):
        # parse model and style
        models = parse_models("model_ids", model_ids, shc)
        color_map = parse_style("style", style)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)
        mean_decimal_year = datetime_to_decimal_year(
            datetime_mean(begin_time, begin_time)
        )

        # parse range bounds
        range_min, range_max = [float(x) for x in dim_range.split(",")]
        logger.debug(
            "output %s data range: %s",
            "logarithmic" if log_scale else "linear",
            (range_min, range_max)
        )

        #TODO: Set these parameters from the inputs.
        elevation = 0
        size_lat, size_lon = resolution, resolution

        def generate_field_lines():
            coord_gdt = empty((size_lat, size_lon, 3))
            coord_gdt[:, :, 1], coord_gdt[:, :, 0] = meshgrid(
                linspace(bbox.lower[1], bbox.upper[1], size_lon),
                linspace(bbox.lower[0], bbox.upper[0], size_lat)
            )
            coord_gdt[:, :, 2] = elevation

            for model_id, model in models.iteritems():
                for point in coord_gdt.reshape((size_lon * size_lat, 3)):
                    # get field-line coordinates and field vectors
                    with ElapsedTimeLogger(
                        "%s field line " % model_id, logger, DEBUG
                    ) as etl:
                        line_coords, line_field = get_field_line(
                            model, point, mean_decimal_year
                        )
                        etl.message += (
                            "with %d points integrated in" % len(line_coords)
                        )
                    # convert coordinates from kilometres to metres
                    line_coords *= 1e3
                    # get scalar field strength
                    line_values = vnorm(line_field)
                    yield model_id, line_coords, line_values

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


def get_field_line(model, point, date):
    # NOTE: The second returned value will be changed from scalar to vector.
    coords, _ = model.field_line(
        point,
        date,
        GEODETIC_ABOVE_WGS84,
        GEOCENTRIC_CARTESIAN,
        check_validity=False
    )
    field = model.eval(
        coords,
        date,
        GEOCENTRIC_CARTESIAN,
        GEOCENTRIC_CARTESIAN,
        secvar=False,
        check_validity=False
    )
    return coords, field
