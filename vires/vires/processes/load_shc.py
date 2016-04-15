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

# NOTE: Loading of this process component is disabled and the code is scheduled
#       for removal. See the eval_model instead.

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

import eoxmagmod as mm
from eoxmagmod import (
    GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN, convert, vrot_sph2cart, vnorm,
)

import matplotlib.cm
from matplotlib.colors import LinearSegmentedColormap
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()

from matplotlib import pyplot

import math
DG2RAD = math.pi / 180.0



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

def diff_row(arr, step=1.0):
        """ Diferentiate 2D array along the row."""
        rstep = 1.0/step
        diff = np.empty(arr.shape)
        diff[:,1:-1,...] = 0.5*rstep*(arr[:,2:,...] - arr[:,:-2,...])
        diff[:,0,...] = rstep*(arr[:,1,...] - arr[:,0,...])
        diff[:,-1,...] = rstep*(arr[:,-1,...] - arr[:,-2,...])
        return diff



class load_shc(Component):
    """ Process to retrieve registered data (focused on Swarm data)
    """
    implements(ProcessInterface)
    abstract = True

    identifier = "load_shc"
    title = "Load and process SHC coefficient file returning image of resulting harmonic expansion"
    metadata = {"test-metadata":"http://www.metadata.com/test-metadata"}
    profiles = ["test_profile"]

    inputs = [
        ("shc", ComplexData('shc',
                title="SHC file data",
                abstract="SHC file data to be processed.",
                formats=(FormatText('text/plain')
            )
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
            default="30000,60000", abstract="Range dimension for visualized parameter",
        )),
        ("style", LiteralData('style', str, optional=True,
            default="jet", abstract="Colormap to be applied to visualization",
        )),
        ("height", LiteralData('height', int, optional=True,
            default=0, abstract="Height above geoid for calculation",
        )),
        ("coefficients_range", LiteralData('coefficients_range', str, optional=True,
            default="-1,-1", abstract="Coefficients range to use for calculation",
        )),
    ]


    outputs = [
        ("output",
            ComplexData('output',
                title="Spehrical expansion result image",
                abstract="Returns the styled result image of the spherical expansion as png",
                formats=(
                    FormatBinaryBase64('image/png'),
                    FormatBinaryRaw('image/png'),
                )
            )
        ),
    ]

    def execute(self, shc, begin_time, end_time, band, dim_range, style, height, coefficients_range, output, **kwarg):
        outputs = {}

        dim_range = [float(x) for x in dim_range.split(",")]
        coefficients_range = [int(x) for x in coefficients_range.split(",")]


        style = get_color_scale(style)


        model = mm.read_model_shc(shc)

        dlat = 0.5
        dlon = 0.5

        #height = 0  
        lat = np.linspace(90.0,-90.0,int(1+180/dlat))
        lon = np.linspace(-180.0,180.0,int(1+360/dlon))


        print lat.size, lon.size 

        coord_wgs84 = np.empty((lat.size, lon.size, 3))
        coord_wgs84[:,:,1], coord_wgs84[:,:,0] = np.meshgrid(lon, lat)
        coord_wgs84[:,:,2] = height

        # evaluate the model 
        mindegree = coefficients_range[0]
        maxdegree = coefficients_range[1]
        

        date = toYearFraction(begin_time, end_time)

        values = model.eval(coord_wgs84, date, GEODETIC_ABOVE_WGS84, GEODETIC_ABOVE_WGS84,
            secvar=False, maxdegree=maxdegree, mindegree=mindegree, check_validity=False)

        # calculate inclination, declination, intensity
        #m_inc, m_dec, m_ints3 = vincdecnorm(m_field)


        #values = model.eval(arr, date, check_validity=False)
        if band == "F":
            plotdata = mm.vnorm(values)
        elif band == "H":
            plotdata = mm.vnorm(values[..., 0:2])
        elif band == "X":
            plotdata = values[..., 0]
        elif band == "Y":
            plotdata = values[..., 1]
        elif band == "Z":
            plotdata = (values[..., 2]*-1)
        elif band == "I":
            plotdata = mm.vincdecnorm(values)[0]
        elif band == "D":
            plotdata = mm.vincdecnorm(values)[1]
        elif band == "X_EW":
            coord_sph = mm.convert(coord_wgs84, mm.GEODETIC_ABOVE_WGS84, mm.GEOCENTRIC_SPHERICAL)
            # derivative along the easting coordinate
            rdist = 1.0/((dlon*DG2RAD)*coord_sph[:,:,2]*np.cos(coord_sph[:,:,0]*DG2RAD))
            plotdata =  diff_row(values[...,0], 1.0)*rdist
        elif band == "Y_EW":
            coord_sph = mm.convert(coord_wgs84, mm.GEODETIC_ABOVE_WGS84, mm.GEOCENTRIC_SPHERICAL)
            rdist = 1.0/((dlon*DG2RAD)*coord_sph[:,:,2]*np.cos(coord_sph[:,:,0]*DG2RAD))
            plotdata =  diff_row(values[...,1], 1.0)*rdist
        elif band == "Z_EW":
            coord_sph = mm.convert(coord_wgs84, mm.GEODETIC_ABOVE_WGS84, mm.GEOCENTRIC_SPHERICAL)
            rdist = 1.0/((dlon*DG2RAD)*coord_sph[:,:,2]*np.cos(coord_sph[:,:,0]*DG2RAD))
            plotdata =  diff_row(values[...,2], 1.0)*rdist


        # the output image
        basename = "%s_%s"%( "shc_result-",uuid4().hex )
        filename_png = "/tmp/%s.png" %( basename )

        try:
            #fig = pyplot.imshow(pix_res,interpolation='nearest')
            #fig = pyplot.imshow(m_field,vmin=dim_range[0], vmax=dim_range[1], interpolation='nearest')
            fig = pyplot.imshow(plotdata, vmin=dim_range[0], vmax=dim_range[1], interpolation='nearest')
            fig.set_cmap(style)
            fig.write_png(filename_png, True)

            result = CDFile(filename_png, **output)

            # with open(filename_png) as f:
            #     output = f.read()

        except Exception as e: 

            if os.path.isfile(filename_png):
                os.remove(filename_png)

            raise e
           
        # else:
        #     os.remove(filename_png)

        #return base64.b64encode(output)
        
        outputs['output'] = result

        return outputs


