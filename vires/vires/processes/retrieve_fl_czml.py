#-------------------------------------------------------------------------------
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Daniel Santillan <daniel.santillan@eox.at>
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

import json
import csv
import math
import struct
import datetime as dt
import time
from itertools import izip
from lxml import etree
from StringIO import StringIO
try:
    # available in Python 2.7+
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict
import numpy as np

from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import InvalidOutputDefError
from eoxserver.services.result import ResultBuffer, ResultFile
from eoxserver.services.ows.wps.parameters import (
    ComplexData, CDObject, CDTextBuffer,
    FormatText, FormatXML, FormatJSON, #FormatBinaryRaw, FormatBinaryBase64,
    BoundingBoxData, BoundingBox,
    LiteralData, String,
    AllowedRange, UnitLinear,
)

from uuid import uuid4
from spacepy import pycdf
from eoxserver.backends.access import connect
from vires import models
from vires.util import get_total_seconds

import eoxmagmod as mm
import matplotlib.cm


from eoxmagmod import (
    vincdecnorm,
    convert, legendre, lonsincos, relradpow, sphargrd, spharpot,
    vrot_sph2geod, vrot_sph2cart, vnorm,
    read_model_wmm2010, read_model_emm2010, read_model_shc,
    read_model_igrf11,
    DATA_WMM_2010, DATA_EMM_2010_STATIC, DATA_EMM_2010_SECVAR,
    DATA_CHAOS5_CORE, DATA_CHAOS5_STATIC, DATA_IGRF11,
    GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
    GEODETIC_ABOVE_EGM96, GEOCENTRIC_CARTESIAN,
    POTENTIAL, GRADIENT, POTENTIAL_AND_GRADIENT,
)



def toYearFraction(dt_start, dt_end):
    def sinceEpoch(date): # returns seconds since epoch
        return time.mktime(date.timetuple())

    date = (dt_end - dt_start)/2 + dt_start  
    s = sinceEpoch

    year = date.year
    startOfThisYear = dt.datetime(year=year, month=1, day=1)
    startOfNextYear = dt.datetime(year=year+1, month=1, day=1)

    yearElapsed = s(date) - s(startOfThisYear)
    yearDuration = s(startOfNextYear) - s(startOfThisYear)
    fraction = yearElapsed/yearDuration

    return date.year + fraction


CRSS = (
    4326,  # WGS84
    32661, 32761,  # WGS84 UPS-N and UPS-S
    32601, 32602, 32603, 32604, 32605, 32606, 32607, 32608, 32609, 32610,  # WGS84 UTM  1N-10N
    32611, 32612, 32613, 32614, 32615, 32616, 32617, 32618, 32619, 32620,  # WGS84 UTM 11N-20N
    32621, 32622, 32623, 32624, 32625, 32626, 32627, 32628, 32629, 32630,  # WGS84 UTM 21N-30N
    32631, 32632, 32633, 32634, 32635, 32636, 32637, 32638, 32639, 32640,  # WGS84 UTM 31N-40N
    32641, 32642, 32643, 32644, 32645, 32646, 32647, 32648, 32649, 32650,  # WGS84 UTM 41N-50N
    32651, 32652, 32653, 32654, 32655, 32656, 32657, 32658, 32659, 32660,  # WGS84 UTM 51N-60N
    32701, 32702, 32703, 32704, 32705, 32706, 32707, 32708, 32709, 32710,  # WGS84 UTM  1S-10S
    32711, 32712, 32713, 32714, 32715, 32716, 32717, 32718, 32719, 32720,  # WGS84 UTM 11S-20S
    32721, 32722, 32723, 32724, 32725, 32726, 32727, 32728, 32729, 32730,  # WGS84 UTM 21S-30S
    32731, 32732, 32733, 32734, 32735, 32736, 32737, 32738, 32739, 32740,  # WGS84 UTM 31S-40S
    32741, 32742, 32743, 32744, 32745, 32746, 32747, 32748, 32749, 32750,  # WGS84 UTM 41S-50S
    32751, 32752, 32753, 32754, 32755, 32756, 32757, 32758, 32759, 32760,  # WGS84 UTM 51S-60S
    0, # ImageCRS
)

class retrieve_fl_czml(Component):
    """ Process to retrieve model field lines as cesium modelling language
    """
    implements(ProcessInterface)

    identifier = "retrieve_fl_czml"
    title = "Retrieve retrieve model field lines as cesium modelling language"
    metadata = {"test-metadata":"http://www.metadata.com/test-metadata"}
    profiles = ["test_profile"]

    inputs = [
        ("model_ids", LiteralData('model_ids', str, optional=False,
            abstract="String input for model identifiers (comma separator)",
        )),
        ("begin_time", LiteralData('begin_time', dt.datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData('end_time', dt.datetime, optional=False,
            abstract="End of the time interval",
        )),
        ("bbox", BoundingBoxData("bbox", crss=CRSS, optional=True,
            default=None,
        )),
        ("resolution", LiteralData('resolution', int, optional=True,
            default=4, abstract="Resolution attribute to define step size for returned elements",
        )),
        ("colors", LiteralData('colors', str, optional=True,
            abstract="Hex colors for requested models (same number as provided model ids)",
        )),
    ]


    outputs = [
        ("output",
            ComplexData('output',
                title="Requested subset of data",
                abstract="Process returns CZML file with calculated field lines",
                formats=FormatText('text/plain')
            )
        ),
    ]

    def execute(self, model_ids, begin_time, end_time, bbox, resolution, colors, **kwarg):
        outputs = {}

        model_ids = model_ids.split(",")
        colors = colors.split(",")

        time = toYearFraction(begin_time, end_time)

        sio = StringIO()

        # file-like text output
        tmp = CDTextBuffer()

        tmp.write('[{"id":"document", "version":"1.0"}')

        for model_id, color in zip(model_ids, colors):

            color = struct.unpack('BBB', color.decode('hex'))

            if model_id == "wmm2010":
                model = read_model_wmm2010()
            elif model_id == "chaos5":
                model = read_model_shc(DATA_CHAOS5_CORE) + read_model_shc(DATA_CHAOS5_STATIC)
            elif model_id == "igrf11":
                model = read_model_igrf11(DATA_IGRF11)

            cnt = 0

            height = 0  
            lat = np.linspace(bbox.lower[0],bbox.upper[0],resolution)
            lon = np.linspace(bbox.lower[1],bbox.upper[1],resolution)


            coord_wgs84 = np.empty((lat.size, lon.size, 3))
            coord_wgs84[:,:,1], coord_wgs84[:,:,0] = np.meshgrid(lon, lat)
            coord_wgs84[:,:,2] = height

            for row in coord_wgs84:
                for point in row:
                    cnt+=1
                    self.handle(model, model_id, time, point, color, tmp, cnt)


        tmp.write(']')
        outputs['output'] = tmp

        return outputs


    def handle(self, model, model_id, date, point, color, tmp, cnt):

        xx = 1e3 * model.field_line(point, date, GEODETIC_ABOVE_WGS84, GEOCENTRIC_CARTESIAN, check_validity=False)

        id = str(uuid4())

        tmp.write(',{"id":"%s-%d","polyline":{"width":2,"material":{"solidColor":{"color":{"rgba":[%d,%d,%d,255]}}},"positions": {"cartesian":%s}}}'
            %(model_id, cnt, color[0], color[1], color[2], translate(xx)))



def translate(arr):

    return "[%s]" % ",".join(("%.0f,%.0f,%.0f" % (vec[0], vec[1], vec[2])) for vec in arr)
