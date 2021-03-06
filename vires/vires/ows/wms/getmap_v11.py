#-------------------------------------------------------------------------------
#
#  VirES for Swarm specific eoxserver WMS 1.1/GetMap service handler.
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2011 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,no-self-use,too-few-public-methods

from eoxserver.core.decoders import kvp, typelist
from eoxserver.resources.coverages import crss
from eoxserver.services.ows.wms.parsing import parse_bbox, parse_time, int_or_str
from eoxserver.services.result import to_http_response
from eoxserver.services.ows.wms.exceptions import InvalidCRS
from .renderer import render_wms_response, SUPPORTED_SRIDS, get_access_logger
from .parsers import get_mean_time


class WMS11GetMapHandler():
    methods = ['GET']
    service = "WMS"
    versions = ("1.1", "1.1.0", "1.1.1")
    request = "GetMap"

    def handle(self, request):
        decoder = WMS11GetMapDecoder(request.GET)

        srid = crss.parseEPSGCode(
            decoder.srs, (crss.fromShortCode, crss.fromURN, crss.fromURL)
        )
        if srid not in SUPPORTED_SRIDS:
            raise InvalidCRS(decoder.srs, "srs")

        minx, miny, maxx, maxy = decoder.bbox

        return to_http_response(render_wms_response(
            layers=decoder.layers,
            srid=srid,
            bbox=(minx, miny, maxx, maxy),
            elevation=decoder.elevation,
            time=get_mean_time(decoder.time),
            width=int(decoder.width),
            height=int(decoder.height),
            response_format=decoder.format,
            query=dict(request.GET),
            logger=get_access_logger(request),
        ))


class WMS11GetMapDecoder(kvp.Decoder):
    layers = kvp.Parameter(type=typelist(str, ","), num=1)
    styles = kvp.Parameter(num="?")
    bbox = kvp.Parameter(type=parse_bbox, num=1)
    time = kvp.Parameter(type=parse_time, num="?")
    srs = kvp.Parameter(num=1)
    width = kvp.Parameter(num=1)
    height = kvp.Parameter(num=1)
    format = kvp.Parameter(num=1)
    dim_bands = kvp.Parameter(type=typelist(int_or_str, ","), num="?")
    elevation = kvp.Parameter(type=float, num="?")
    dimensions = kvp.MultiParameter(lambda s: s.startswith("dim_"), locator="dimension", num="*")
