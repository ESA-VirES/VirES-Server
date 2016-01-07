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

import os 
from uuid import uuid4
import os.path
import base64
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
    ComplexData, CDObject, CDTextBuffer, CDFile, 
    FormatText, FormatXML, FormatJSON, FormatBinaryRaw, FormatBinaryBase64,
    BoundingBoxData, BoundingBox,
    LiteralData, String,
    AllowedRange, UnitLinear,
)



from vires.util import get_total_seconds
from vires.util import get_color_scale
from vires.util import get_model

import eoxmagmod as mm
from eoxmagmod import (
    GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN, convert, vrot_sph2cart, vnorm,
)

import matplotlib.cm
from matplotlib.colors import LinearSegmentedColormap
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()

import matplotlib as mpl
mpl.use('Agg')
from matplotlib import pyplot



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



class calc_diff(Component):
    """ Process to retrieve registered data (focused on Swarm data)
    """
    implements(ProcessInterface)

    identifier = "calc_diff"
    title = "Calculate the difference between registered models or uploaded shc file"
    metadata = {"test-metadata":"http://www.metadata.com/test-metadata"}
    profiles = ["test_profile"]

    inputs = [
        ("shc", ComplexData('shc',
                title="SHC file data",
                abstract="SHC file data to be processed.",
                optional=True,
                formats=(FormatText('text/plain'),
            )
        )),
        ("model_ids", LiteralData('model_ids', str, optional=False,
            abstract="One model id to compare to shc model or two comma separated ids",
        )),
        ("begin_time", LiteralData('begin_time', dt.datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData('end_time', dt.datetime, optional=False,
            abstract="End of the time interval",
        )),
        ("band", LiteralData('band', str, optional=True,
            default="F", abstract="Band wished to be visualized",
        )),
        ("dim_range", LiteralData('dim_range', str, optional=True,
            default="0,100", abstract="Range dimension for visualized parameter",
        )),
        ("style", LiteralData('style', str, optional=True,
            default="jet", abstract="Colormap to be applied to visualization",
        )),
        ("height", LiteralData('height', int, optional=True,
            default=0, abstract="Height above geoid for calculation",
        )),
    ]


    outputs = [
        ("difference_image",
            ComplexData('difference_image',
                title="Spehrical expansion result image",
                abstract="Returns the styled result image of the spherical expansion as png",
                formats=(
                    FormatBinaryBase64('image/png'),
                    FormatBinaryRaw('image/png'),
                )
            )
        ),
        ("style_range", LiteralData('style_range', str,
            abstract="Range and style definition as string"
        )),
    ]

    def execute(self, shc, model_ids, begin_time, end_time, band, dim_range, style, height, difference_image, **kwarg):
        outputs = {}

        style_str = style
        style = get_color_scale(style)

        dim_range = [float(x) for x in dim_range.split(",")]

        m1 = None
        m2 = None

        model_ids = model_ids.split(",")

        # Two model ids are passed
        if len(model_ids) == 2:
            m1 = get_model(model_ids[0])
            m2 = get_model(model_ids[1])

        # One model id passed to compare to shc file
        elif len(model_ids) == 1:
            m1 = get_model(model_ids[0])
            m2 = mm.read_model_shc(shc)

        else:
            # TODO: Can i handle the error like this?
            raise Exception("Either two model ids or a model id and a shc file need to be provided")


        model = m1 - m2

        dlat = 0.5
        dlon = 0.5

        lat = np.linspace(90.0,-90.0,int(1+180/dlat))
        lon = np.linspace(-180.0,180.0,int(1+360/dlon))

        print lat.size, lon.size 

        coord_wgs84 = np.empty((lat.size, lon.size, 3))
        coord_wgs84[:,:,1], coord_wgs84[:,:,0] = np.meshgrid(lon, lat)
        coord_wgs84[:,:,2] = height

        # evaluate the model 
        maxdegree = -1 
        mindegree = -1 

        date = toYearFraction(begin_time, end_time)

        m_ints3 = vnorm(model.eval(coord_wgs84, date, GEODETIC_ABOVE_WGS84, GEODETIC_ABOVE_WGS84,
            secvar=False, maxdegree=maxdegree, mindegree=mindegree, check_validity=False))

        dim_range[0] = np.amin(m_ints3) 
        dim_range[1] = np.amax(m_ints3) 

        # the output image
        basename = "%s_%s"%( "shc_result-",uuid4().hex )
        filename_png = "/tmp/%s.png" %( basename )

        try:
            #fig = pyplot.imshow(pix_res,interpolation='nearest')
            #fig = pyplot.imshow(m_field,vmin=dim_range[0], vmax=dim_range[1], interpolation='nearest')
            fig = pyplot.imshow(m_ints3, vmin=dim_range[0], vmax=dim_range[1], interpolation='nearest')
            fig.set_cmap(style)
            fig.write_png(filename_png, True)

            result = CDFile(filename_png, **difference_image)

            # with open(filename_png) as f:
            #     output = f.read()

        except Exception as e: 

            if os.path.isfile(filename_png):
                os.remove(filename_png)

            raise e
           
        # else:
        #     os.remove(filename_png)

        #return base64.b64encode(output)
        
        outputs['difference_image'] = result
        outputs['style_range'] = "%s,%s,%s"%(style_str, dim_range[0], dim_range[1])

        return outputs


