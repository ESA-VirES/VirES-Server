#-------------------------------------------------------------------------------
#
# Project: VirES
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
from eoxserver.core.util import timetools
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import InvalidOutputDefError
from eoxserver.services.result import ResultBuffer, ResultFile
from eoxserver.services.ows.wps.parameters import (
    ComplexData, CDObject, CDAsciiTextBuffer, CDFile, 
    FormatText, FormatXML, FormatJSON, FormatBinaryRaw, FormatBinaryBase64,
    BoundingBoxData, BoundingBox,
    LiteralData, String,
    AllowedRange, UnitLinear,
)

from uuid import uuid4
from spacepy import pycdf
from eoxserver.backends.access import connect
from vires import models
from vires.util import get_total_seconds
from vires.util import get_model
from vires import aux

import eoxmagmod as mm

def toYearFractionInterval(dt_start, dt_end):
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


def toYearFraction(date):
    def sinceEpoch(date): # returns seconds since epoch
        return time.mktime(date.timetuple())
 
    s = sinceEpoch

    year = date.year
    startOfThisYear = dt.datetime(year=year, month=1, day=1)
    startOfNextYear = dt.datetime(year=year+1, month=1, day=1)

    yearElapsed = s(date) - s(startOfThisYear)
    yearDuration = s(startOfNextYear) - s(startOfThisYear)
    fraction = yearElapsed/yearDuration

    return date.year + fraction



def getModelResidualIdentifiers(modelid):
    if modelid == "CHAOS-5-Combined":
        return  ("B_N_res_CHAOS-5-Combined", "B_E_res_CHAOS-5-Combined", "B_C_res_CHAOS-5-Combined", "F_res_CHAOS-5-Combined")
    if modelid == "EMM":
        return  ("B_N_res_EMM", "B_E_res_EMM", "B_C_res_EMM", "F_res_EMM")
    if modelid == "IGRF":
        return  ("B_N_res_IGRF", "B_E_res_IGRF", "B_C_res_IGRF", "F_res_IGRF")
    if modelid == "IGRF12":
        return  ("B_N_res_IGRF12", "B_E_res_IGRF12", "B_C_res_IGRF12", "F_res_IGRF12")
    if modelid == "SIFM":
        return  ("B_N_res_SIFM", "B_E_res_SIFM", "B_C_res_SIFM", "F_res_SIFM")
    if modelid == "WMM":
        return  ("B_N_res_WMM", "B_E_res_WMM", "B_C_res_WMM", "F_res_WMM")
    if modelid == "Custom_Model":
        return  ("B_N_res_Custom_Model", "B_E_res_Custom_Model", "B_C_res_Custom_Model", "F_res_Custom_Model")


class retrieve_data_filtered(Component):
    """ Process to retrieve a subset of registered data (focused on Swarm data) by a set of filters
    """
    implements(ProcessInterface)

    identifier = "retrieve_data_filtered"
    title = "Retrieve registered Swarm data based on collection, time intervall and filters"
    metadata = {"test-metadata":"http://www.metadata.com/test-metadata"}
    profiles = ["test_profile"]

    inputs = [
        ("collection_ids", LiteralData('collection_ids', str, optional=False,
            abstract="String input for collection identifiers (semicolon separator)",
        )),
        ("shc", ComplexData('shc',
                title="SHC file data",
                abstract="SHC file data to be processed.",
                optional=True,
                formats=(FormatText('text/plain'),
            )
        )),
        ("model_ids", LiteralData('model_ids', str, optional=True, default="",
            abstract="One model id to compare to shc model or two comma separated ids",
        )),
        ("begin_time", LiteralData('begin_time', dt.datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData('end_time', dt.datetime, optional=False,
            abstract="End of the time interval",
        )),
        ("filters", LiteralData('filters', str, optional=True,
            abstract="""Set of filters defined by user, identifier and extent are separated by a colon,
             both extent values are separated by a comma and filters are separated by semicolon; 
             Example 'F:10000,20000;Latitude:-50,50'""", default=None,
        )),

    ]


    outputs = [
        ("output",
            ComplexData('output',
                title="Requested subset of data",
                abstract="Process returns subset of data defined by time, filters and collections.",
                formats=(
                    FormatText('text/csv'),
                    FormatBinaryRaw("application/cdf")
                )
            )
        ),
    ]

    def execute(self, collection_ids, shc, model_ids, begin_time, end_time, filters, output, **kwarg):

        collection_ids = collection_ids.split(",")

        if filters:
            filter_input = filters.split(";")
            filters={}

            for elem in filter_input:
                f_id, f_range = elem.split(":")
                f_range = [float(x) for x in f_range.split(",")]
                filters[f_id] = f_range


        collections = models.ProductCollection.objects.filter(identifier__in=collection_ids)
        range_type = collections[0].range_type


        model_ids = model_ids.split(",")
        mm_models = [get_model(x) for x in model_ids]

        if len(mm_models)>0 and mm_models[0] is None:
            mm_models = []
            model_ids = []

        if shc:
            model_ids.append("Custom_Model")
            mm_models.append(mm.read_model_shc(shc))

        add_range_type = []
        if len(model_ids)>0 and model_ids[0] != '':
            for mid in model_ids:
                    add_range_type.append("F_res_%s"%(mid))
                    add_range_type.append("B_NEC_res_%s"%(mid))

        results = []
        total_amount = 0

        bt = timetools.isoformat(begin_time).translate(None, 'Z:-')
        et = timetools.isoformat(end_time).translate(None, 'Z:-')
        resultname = "%s_%s_%s_MDR_MAG_LR_Filtered"%("_".join(collection_ids),bt,et)

        if output['mime_type'] == "text/csv":
            output_filename = "/tmp/%s.csv" % uuid4().hex
            
            with open(output_filename, "w") as fout:

                writer = csv.writer(fout)
                first = True

                for collection_id in collection_ids:
                    coverages_qs = models.Product.objects.filter(collections__identifier=collection_id)
                    coverages_qs = coverages_qs.filter(begin_time__lte=end_time)
                    coverages_qs = coverages_qs.filter(end_time__gte=begin_time)

                    for coverage in coverages_qs:
                        cov_begin_time, cov_end_time = coverage.time_extent
                        cov_cast = coverage.cast()
                        t_res = get_total_seconds(cov_cast.resolution_time)
                        low = max(0, int(get_total_seconds(begin_time - cov_begin_time) / t_res))
                        high = min(cov_cast.size_x, int(math.ceil(get_total_seconds(end_time - cov_begin_time) / t_res)))
                        result, count = self.handle(cov_cast, collection_id, range_type, low, high, begin_time, end_time, mm_models, model_ids, filters)
                        total_amount += count
                        if (total_amount) > (432e3): # equivalent to five complete days of swarm data
                            raise Exception("Requested data too large: %d, please refine filters"%total_amount)

                        if first:
                            writer.writerow(result.keys())
                            for row in izip(*result.values()):
                                writer.writerow(map(translate, row))
                            first = False
                        else:
                            for row in izip(*result.values()):
                                writer.writerow(map(translate, row))

            return CDFile(output_filename, filename=(resultname+".csv"), **output)

        elif output['mime_type'] in ("application/cdf", "application/x-cdf"):
            #encoder = CDFEncoder(params.rangesubset)
            output_filename = "/tmp/%s.cdf" % uuid4().hex

            with pycdf.CDF(output_filename, '') as output_ds:
                #output_ds = pycdf.CDF(output_filename, '')

                for collection_id in collection_ids:
                    coverages_qs = models.Product.objects.filter(collections__identifier=collection_id)
                    coverages_qs = coverages_qs.filter(begin_time__lte=end_time)
                    coverages_qs = coverages_qs.filter(end_time__gte=begin_time)

                    for coverage in coverages_qs:
                        cov_begin_time, cov_end_time = coverage.time_extent
                        cov_cast = coverage.cast()
                        t_res = get_total_seconds(cov_cast.resolution_time)
                        low = max(0, int(get_total_seconds(begin_time - cov_begin_time) / t_res))
                        high = min(cov_cast.size_x, int(math.ceil(get_total_seconds(end_time - cov_begin_time) / t_res)))
                        result, count = self.handle(cov_cast, collection_id, range_type, low, high, begin_time, end_time, mm_models, model_ids, filters)
                        total_amount += count
                        if (total_amount) > (432e3): # equivalent to five complete days of swarm data
                            raise Exception("Requested data too large: %d, please refine filters"%total_amount)

                        for name, data in result.items():
                            output_ds[name] = data

            return CDFile(output_filename, filename=(resultname+".cdf"), **output)

        else:
            ExecuteError("Unexpected output format requested! %r"%output['mime_type'])

        return _encode_data(merged_result, output, resultname)


    def handle(self, coverage, collection_id, range_type, low, high, begin_time, end_time, mm_models, model_ids, filters):
        # Open file
        filename = connect(coverage.data_items.all()[0])

        with pycdf.CDF(filename) as ds:
            #ds = pycdf.CDF(filename)
            output_data = OrderedDict()

            # Read data
            for band in range_type:
                data = ds[band.identifier]
                output_data[band.identifier] = data[low:high]


            if filters:

                band_names = [band.identifier for band in range_type]

                # First filter by all possible parameters of the data
                mask = True

                for filter_name, filter_value in filters.items():
                    if filter_name in band_names:
                        data = output_data[filter_name]
                        mask = mask & (data >= filter_value[0]) & (data <= filter_value[1])
                     # Check for single parameter filter of 3D vectors
                    if filter_name in ("B_N", "B_E", "B_C"):
                        index = ("B_N", "B_E", "B_C").index(filter_name)
                        data = output_data["B_NEC"][:,index]
                        mask = mask & (data >= filter_value[0]) & (data <= filter_value[1])


                # Only apply mask if something was added to the mask (i.e. not boolean)
                if not isinstance(mask, bool):
                    for name, data in output_data.items():
                        output_data[name] = output_data[name][mask]

                
                # Filter for possible kp and Dst indices
                filter_names = [filter_name for filter_name in filters.keys() if filter_name in ("dst", "kp")]
                if filter_names:
                    aux_data = aux.query_db(
                        output_data["Timestamp"][0], output_data["Timestamp"][-1],
                        len(output_data["Timestamp"])
                    )
                    mask = True
                    for fn in filter_names:
                        data = aux_data[fn]
                        mask = mask & (data >= filters[fn][0]) & (data <= filters[fn][1])

                    # Only apply mask if something was added to the mask (i.e. not boolean)
                    if not isinstance(mask, bool):
                        for name, data in output_data.items():
                            output_data[name] = output_data[name][mask]


                # Filter for possible residuals
                for model_id, model in zip(model_ids, mm_models):
                    filter_names = [
                        filter_name
                        for filter_name in filters.keys()
                        if filter_name in getModelResidualIdentifiers(model_id)
                    ]
                    if filter_names:
                        # One of the filters is based on model residuals so we calculate model for values
                        rads = output_data["Radius"]*1e-3
                        coords_sph = np.vstack((output_data["Latitude"], output_data["Longitude"], rads)).T
                        model_data = model.eval(coords_sph, toYearFractionInterval(begin_time, end_time), mm.GEOCENTRIC_SPHERICAL, check_validity=False)
                        model_data[:,2] *= -1

                        data_res = output_data["F"] - mm.vnorm(model_data)
                        data_res_vec = output_data["B_NEC"] - model_data

                        mask = True

                        for fn in filter_names:
                            if "B_N_res_" in fn:
                                data = data_res_vec[:,0]
                                mask = mask & (data >= filters[fn][0]) & (data <= filters[fn][1])
                            if "B_E_res_" in fn:
                                data = data_res_vec[:,1]
                                mask = mask & (data >= filters[fn][0]) & (data <= filters[fn][1])
                            if "B_C_res_" in fn:
                                data = data_res_vec[:,2]
                                mask = mask & (data >= filters[fn][0]) & (data <= filters[fn][1])
                            if "F_res_" in fn:
                                mask = mask & (data_res >= filters[fn][0]) & (data_res <= filters[fn][1])
                        
                        if not isinstance(mask, bool):
                            for name, data in output_data.items():
                                output_data[name] = output_data[name][mask]


                # Filter for possible residuals to custom model


                #Filter for possible qdlat or mlt
                filter_names = [filter_name for filter_name in filters.keys() if filter_name in ("qdlat", "mlt")]
                if filter_names:
                    rads = output_data["Radius"]*1e-3
                    times = map(toYearFraction, output_data["Timestamp"])
                    qdlat, qdlon, mlt = mm.eval_apex(output_data["Latitude"], output_data["Longitude"], rads, times)
                    mask = True

                    for fn in filter_names:
                        if fn == "qdlat":
                            mask = mask & (qdlat >= filters[fn][0]) & (qdlat <= filters[fn][1])
                        if fn == "mlt":
                            mask = mask & (mlt >= filters[fn][0]) & (mlt <= filters[fn][1])
                    
                    if not isinstance(mask, bool):
                        for name, data in output_data.items():
                            output_data[name] = output_data[name][mask]

            count = len(output_data["Latitude"])

            return output_data, count

        
def translate(arr):

    try:
        if arr.ndim == 1:
            return "{%s}" % ";".join(map(str, arr))
    except:
        pass

    return arr


def _encode_data(output_data, output, resultname):

    if output['mime_type'] == "text/csv":
        output_filename = "/tmp/%s.csv" % uuid4().hex
        
        with open(output_filename, "w") as fout:
            writer = csv.writer(fout)
            writer.writerow(output_data.keys())
            for row in izip(*output_data.values()):
                writer.writerow(map(translate, row))

        return CDFile(output_filename, filename=(resultname+".csv"), **output)

    elif output['mime_type'] in ("application/cdf", "application/x-cdf"):
        #encoder = CDFEncoder(params.rangesubset)
        output_filename = "/tmp/%s.cdf" % uuid4().hex
        output_ds = pycdf.CDF(output_filename, '')

        for name, data in output_data.items():
            output_ds[name] = data

        output_ds.save()
        output_ds.close()

        return CDFile(output_filename, filename=(resultname+".cdf"), **output)

    else:
        ExecuteError("Unexpected output format requested! %r"%output['mime_type'])

    
