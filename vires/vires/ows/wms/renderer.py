#-------------------------------------------------------------------------------
#
#  VirES for Swarm specific - WMS response rendering
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
# pylint: disable=too-many-arguments,too-many-boolean-expressions,too-many-locals

from logging import getLogger
from eoxserver.services.ows.wps.v10.encoders.execute_response_raw import ResultAlt
from eoxserver.core.decoders import InvalidParameterException
from vires.time_util import datetime_to_mjd2000, naive_to_utc
from vires.access_util import AccessLoggerAdapter, get_username, get_remote_addr
from vires.processes.util import parse_style, render_model
from .parsers import (
    get_models, parse_query_parameter, parse_colormaps, parse_bool,
    parse_value_range, parse_variable,
)


SUPPORTED_SRIDS = (4326,)
SUPPORTED_FORMATS = ("image/png",)
MAX_IMAGE_SIZE = (2048, 2048)


def render_wms_response(layers, srid, bbox, elevation, time, width, height,
                        response_format, query, logger):
    """ Render WMS response. """
    check_inputs(
        layers, srid, bbox, elevation, time, width, height, response_format,
    )

    is_transparent = parse_query_parameter(
        query, "transparent", parse_bool, default=[""], multiple_values=True
    )[-1]
    colormaps = parse_query_parameter(
        query, "styles", parse_colormaps, multiple_values=True
    )[-1]
    colormaps = (
        colormaps[:len(layers)] + [""]*max(0, len(layers) - len(colormaps))
    )
    value_range = parse_query_parameter(query, "dim_range", parse_value_range)
    variable = parse_query_parameter(query, "dim_bands", parse_variable)

    models = select_models(layers, get_models(query, layers))

    logger.info(
        "request: time: %s, aoi: %s, elevation: %g, "
        "model: %s, variable: %s, image-size: (%d, %d), mime-type: %s",
        naive_to_utc(time).isoformat("T"),
        bbox, elevation, models[-1].full_expression,
        variable, width, height, response_format,
    )

    payload, content_type, value_range = render_model(
        model=models[-1],
        variable=variable,
        mjd2000=datetime_to_mjd2000(naive_to_utc(time)),
        srid=srid,
        bbox=bbox,
        elevation=elevation,
        size=(width, height),
        value_range=value_range,
        colormap=parse_style("style", colormaps[-1]),
        response_format=response_format,
        is_transparent=is_transparent,
    )

    return encode_response(payload, content_type)


def check_inputs(layers, srid, bbox, elevation, time, width, height,
                 response_format):
    """ Check the input parameters. """
    if not layers:
        raise InvalidParameterException("No layers specified", "layers")

    if time is None:
        raise InvalidParameterException(
            "Missing mandatory 'time' parameter", "time"
        )

    if response_format not in SUPPORTED_FORMATS:
        raise InvalidParameterException(
            "Unsupported format %r!" % response_format, "format"
        )

    if width < 1:
        raise InvalidParameterException("Invalid image width!", "width")
    if width > MAX_IMAGE_SIZE[0]:
        raise InvalidParameterException("Image width too high!", "width")

    if height < 1:
        raise InvalidParameterException("Invalid Image height!", "height")
    if height > MAX_IMAGE_SIZE[1]:
        raise InvalidParameterException("Image height too high!", "height")

    minx, miny, maxx, maxy = bbox

    if elevation < 0 or elevation > 1000000:
        raise InvalidParameterException("Invalid elevation!", "elevation")

    if srid == 4326 and (
            minx < -180 or minx > 180 or
            maxx < -180 or maxx > 180 or
            miny < -90 or miny > 90 or
            maxy < -90 or maxy > 90
        ):
        raise InvalidParameterException(
            "Invalid geographic extent!", "bbox"
        )


def select_models(layers, models):
    """ Select requested models. """
    model_dict = {model.name: model for model in models}
    return [model_dict[layer] for layer in layers]


def encode_response(payload, content_type, headers=None, filename=None):
    """ Encode raw complex data."""
    return ResultAlt(
        payload, content_type=content_type, filename=filename, headers=headers,
    ),


def get_access_logger(request):
    """ Get access logger wrapped by the AccessLoggerAdapter """
    return AccessLoggerAdapter(
        getLogger("access.wms.eval_model"),
        username=get_username(request),
        remote_addr=get_remote_addr(request),
    )
