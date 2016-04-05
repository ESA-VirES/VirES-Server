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
import math
import csv
import datetime as dt
from itertools import izip
from itertools import izip_longest
import time
from StringIO import StringIO
try:
    # available in Python 2.7+
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict
import numpy as np

from django.conf import settings
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
from eoxserver.backends.access import connect
from vires import models
from vires.util import get_total_seconds
from vires.aux import query_dst, query_kp
from vires.time_util import mjd2000_to_datetime


class get_indices(Component):
    """ Process to retrieve registered auxiliary data
    """
    implements(ProcessInterface)

    identifier = "get_indices"
    title = "Retrieve registered auxiliary indices based on start and end time"
    metadata = {"test-metadata":"http://www.metadata.com/test-metadata"}
    profiles = ["test_profile"]

    inputs = [
        ("index_id", LiteralData('index_id', str, optional=False,
            abstract="Index id from which auxiliary data will be retrieved",
            allowed_values=('kp','dsp'),
        )),
        ("begin_time", LiteralData('begin_time', dt.datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData('end_time', dt.datetime, optional=False,
            abstract="End of the time interval",
        )),
    ]


    outputs = [
        ("output",
            ComplexData('output',
                title="Requested subset of data",
                abstract="Process returns subset of data defined by time, bbox and collections.",
                formats=FormatText('text/plain')
            )
        ),
    ]

    def execute(self, index_id, begin_time, end_time, **kwarg):
        outputs = {}

        output_data = OrderedDict()

        f = StringIO()
        writer = csv.writer(f)

        writer.writerow(["id","value", "time"])

        if index_id == "dst":
            aux_data = query_dst(
                settings.VIRES_AUX_DB_DST, begin_time, end_time
            )
        elif index_id == "kp":
            aux_data = query_kp(
                settings.VIRES_AUX_DB_KP, begin_time, end_time
            )
        #elif index_id == "ibia":
        #    aux_data = aux.query_ibi_ni(
        #        "A", begin_time, end_time
        #    )
        #    index_id = "bubble_index"

        t_arr = np.array(aux_data["time"]) 
        v_arr = np.array(aux_data[index_id])

        if t_arr.size > 500:

            bin_size = (t_arr.size - 1)/500 + 1 
            bin_count = t_arr.size / bin_size
            size_short = bin_size * bin_count
            axis = 1

            t_arr_new = np.average(t_arr[:size_short].reshape((bin_count, bin_size)), axis)

            v_arr_max = np.amax(v_arr[:size_short].reshape((bin_count, bin_size)), axis)
            v_arr_min = np.amin(v_arr[:size_short].reshape((bin_count, bin_size)), axis)

            t_arr = t_arr_new
            v_arr = [ v_max if abs(v_max) > abs(v_min) else v_min for v_max, v_min in izip(v_arr_max, v_arr_min) ]

        t_arr = map(mjd2000_to_datetime, t_arr)

        for row in izip(v_arr, t_arr):
            writer.writerow([index_id] + map(translate, row))

        outputs['output'] = f
        
        return outputs


def translate(arr):
    try:
        if arr.ndim == 1:
            return "{%s}" % ";".join(map(str, arr))
    except:
        pass

    return arr
