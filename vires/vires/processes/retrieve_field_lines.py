#-------------------------------------------------------------------------------
#
# WPS process calculating magnetic field-lines from models.
#
# Deprecated. Replaced by vires:fetch_fieldlines process.
# To be removed after the completed client transition to the new process.
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
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
# pylint: disable=too-many-arguments,too-many-locals
# pylint: disable=too-few-public-methods,no-self-use,unused-argument

from collections import defaultdict
from io import BytesIO
from datetime import datetime
import msgpack
from numpy import empty, linspace, meshgrid, asarray
from eoxmagmod import (
    GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN, EARTH_RADIUS,
    trace_field_line, convert, vnorm,
)
from eoxserver.services.ows.wps.parameters import (
    LiteralData, BoundingBoxData, ComplexData, CDFileWrapper, CDObject,
    FormatText, FormatJSON, FormatBinaryRaw, AllowedRange,
)
from eoxserver.services.ows.wps.exceptions import InvalidOutputDefError
from vires.time_util import datetime_to_mjd2000, naive_to_utc, format_datetime
from vires.perf_util import ElapsedTimeLogger
from vires.processes.base import WPSProcess
from vires.processes.util import parse_model_list, get_extra_model_parameters

EARTH_RADIUS_M = EARTH_RADIUS * 1e3 # mean Earth radius in meters
TRACE_OPTIONS = {'max_radius': 25 * EARTH_RADIUS}


class RetrieveFieldLines(WPSProcess):
    """ This process generates a set of field lines passing trough the given
    area of interest.
    """
    identifier = "retrieve_field_lines"
    title = "Generate field lines"
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
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
        ("time", LiteralData(
            'time', datetime, optional=False,
            abstract="Time at which the fields lines are calculated.",
        )),
        ("height", LiteralData(
            "height", float, optional=True, uoms=(("km", 1.0), ("m", 1e-3)),
            default=0.0, allowed_values=AllowedRange(-1., 1000., dtype=float),
            abstract=(
                "Height above the mean Earth radius at which the staring points"
                " are located."
            ),
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
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Fields lines",
            abstract="Calculated field lines and coloured field strength.",
            formats=(
                FormatJSON(),
                FormatBinaryRaw("application/msgpack"),
                FormatBinaryRaw("application/x-msgpack"),
            )
        )),
    ]

    def execute(self, model_ids, shc, time, height, bbox, lines_per_col,
                lines_per_row, output, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        # parse model and style
        models, _ = parse_model_list("model_ids", model_ids, shc)

        # fix the time-zone of the naive date-time
        mjd2000 = datetime_to_mjd2000(naive_to_utc(time))

        access_logger.info(
            "request: toi: %s, aoi: %s, elevation: %g, "
            "models: (%s), grid: (%d, %d)",
            format_datetime(time),
            bbox[0]+bbox[1] if bbox else (-90, -180, 90, 180), height,
            ", ".join(
                "%s = %s" % (model.name, model.full_expression)
                for model in models
            ),
            lines_per_col, lines_per_row,
        )

        def generate_field_lines():
            n_lines = lines_per_row * lines_per_col
            coord_geo = empty((lines_per_col, lines_per_row, 3))
            coord_geo[..., 1], coord_geo[..., 0] = meshgrid(
                linspace(bbox.lower[1], bbox.upper[1], lines_per_row),
                linspace(bbox.lower[0], bbox.upper[0], lines_per_col)
            )
            coord_geo[..., 2] = height + EARTH_RADIUS

            total_count = 0
            for model in models:
                model_count = 0

                options = get_extra_model_parameters(
                    mjd2000, model.model.parameters
                )

                self.logger.debug(
                    "%s=%s model options: %s",
                    model.name, model.full_expression, options
                )

                for point in coord_geo.reshape((n_lines, 3)):
                    # get field-line coordinates and field vectors
                    with ElapsedTimeLogger(
                            "%s=%s field line " % (model.name, model.full_expression),
                            self.logger
                        ) as etl:
                        line_coords, line_field = trace_field_line(
                            model.model, mjd2000, point,
                            GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN,
                            trace_options=TRACE_OPTIONS, model_options=options,
                        )
                        etl.message += (
                            "with %d points integrated in" % len(line_coords)
                        )

                    # convert coordinates from kilometres to metres
                    yield (model.name, point, 1e3*line_coords, vnorm(line_field))
                    model_count += line_coords.shape[0]

                access_logger.info(
                    "model: %s=%s, lines: %d, points: %d",
                    model.name, model.full_expression, n_lines, model_count,
                )
                total_count += model_count

            access_logger.info(
                "response: lines: %d, points: %d, mime-type: %s",
                n_lines * len(models), total_count, output['mime_type'],
            )

        # data colouring
        field_lines = generate_field_lines()
        info = {
            'time': format_datetime(naive_to_utc(time)),
            'models': {model.name: model.full_expression for model in models},
            'bbox': bbox[0]+bbox[1] if bbox else (-90, -180, 90, 180),
            'height': height*1e3,
            'rows': lines_per_col,
            'cols': lines_per_row,
        }

        if output['mime_type'] == "application/json":
            return self._write_json(field_lines, info, output)
        if output['mime_type'] in ("application/msgpack", "application/x-msgpack"):
            return self._write_msgpack(field_lines, info, output)
        raise InvalidOutputDefError(
            'output',
            "Unexpected output format %r requested!" % output['mime_type']
        )

    @classmethod
    def _write_json(cls, field_lines, info, output):
        result = cls._serialize(field_lines, info)
        return CDObject(result, format=FormatJSON(), **output)

    @classmethod
    def _write_msgpack(cls, field_lines, info, output):
        result = cls._serialize(field_lines, info)
        output_fobj = BytesIO()
        msgpack.pack(result, output_fobj)
        return CDFileWrapper(output_fobj, **output)

    @classmethod
    def _serialize(cls, field_lines, info):
        # NOTE: For a seamless transition, both values and colours are exported.
        # The colours will be removed eventually.
        fieldlines = defaultdict(list)
        for model_id, start, coords, values in field_lines:
            coords = convert(coords, GEOCENTRIC_CARTESIAN, GEOCENTRIC_SPHERICAL)
            apex_point, apex_height = cls._find_apex(coords)
            ground_points = cls._find_ground_intersection(coords)
            fieldlines[model_id].append({
                'start_point': start.tolist(),
                'ground_points': ground_points.tolist(),
                'apex_point': None if apex_point is None else apex_point.tolist(),
                'apex_height': apex_height,
                'coordinates': coords.tolist(),
                'values': values.tolist(),
            })
        return {
            'info': info,
            'fieldlines': dict(fieldlines),
        }

    @staticmethod
    def _find_apex(coords):
        """ Find the field-line apex. """
        radius = coords[:, 2]
        idx = radius.argmax()
        # the apex must not be the first or last coordinate
        if 0 < idx < radius.size - 1:
            return coords[idx, :], radius[idx] - EARTH_RADIUS_M
        return None, None

    @staticmethod
    def _find_ground_intersection(coords):
        """ Find the field-line ground intersection. """
        points = []
        height = coords[:, 2] - EARTH_RADIUS_M
        mask = height > 0
        idx_intersections, = (mask[1:] ^ mask[:-1]).nonzero()
        for idx in idx_intersections:
            alpha = height[idx] / (height[idx] - height[idx+1])
            points.append((1 - alpha)*coords[idx] + alpha*coords[idx+1])
        return asarray(points)
