#-------------------------------------------------------------------------------
#
# Data retrieval WPS process
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
# pylint: disable=too-many-arguments, too-many-locals, missing-docstring
# pylint: disable=too-many-statements, no-self-use

from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import izip
from cStringIO import StringIO
from numpy import arange
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, CDFileWrapper,
)
from eoxserver.backends.access import connect
from vires.util import datetime_array_slice
from vires.time_util import naive_to_utc
from vires.cdf_util import (
    cdf_open, cdf_rawtime_to_mjd2000,
    cdf_rawtime_to_datetime, cdf_rawtime_to_unix_epoch,
)
from vires.models import ProductCollection, Product
from vires.processes.base import WPSProcess

REQUIRED_FIELDS = [
    "Timestamp", "Bubble_Probability",
]

# time selection tolerance
TIME_TOLERANCE = timedelta(microseconds=10)

CDF_RAW_TIME_CONVERTOR = {
    "ISO date-time": cdf_rawtime_to_datetime,
    "MJD2000": cdf_rawtime_to_mjd2000,
    "Unix epoch": cdf_rawtime_to_unix_epoch,
}


class RetrieveBubbleIndex(WPSProcess):
    """ Process for retriving information of timespans covered by bubbles
    """
    identifier = "retrieve_bubble_index"
    title = "Retrieve filtered Swarm data."
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("collection_id", LiteralData(
            'collection_id', str, optional=False,
            title="Bubble index collection identifier",
            abstract="Bubble index collection identifier",
        )),
        ("begin_time", LiteralData(
            'begin_time', datetime, optional=False, title="Begin time",
            abstract="Start of the selection time interval",
        )),
        ("end_time", LiteralData(
            'end_time', datetime, optional=False, title="End time",
            abstract="End of the selection time interval",
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Output data",
            formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def execute(self, collection_id, begin_time, end_time, output, **kwarg):

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)

        output_fobj = StringIO()

        collection = ProductCollection.objects.filter(
            identifier=collection_id
        )

        # TODO: assert that the range_type is equal for collection
        # prepare fields
        data_fields = [
            field.identifier for field in collection[0].range_type
            if field.identifier in REQUIRED_FIELDS
        ]

        # write CSV header flag
        initialize = True

        products_qs = Product.objects.filter(
            collections__identifier=collection_id,
            begin_time__lte=(end_time + TIME_TOLERANCE),
            end_time__gte=(begin_time - TIME_TOLERANCE),
        ).order_by('begin_time')

        for product in (item.cast() for item in products_qs):

            time_first, time_last = product.time_extent
            low, high = datetime_array_slice(
                begin_time, end_time, time_first, time_last,
                product.sampling_period, TIME_TOLERANCE
            )

            data, _, cdf_type = self.handle(
                product, data_fields, low, high, 1
            )

            # convert the time format
            data['Timestamp'] = (
                CDF_RAW_TIME_CONVERTOR["ISO date-time"](
                    data['Timestamp'], cdf_type['Timestamp']
                )
            )

            if initialize:
                output_fobj.write(','.join(
                    '"{0}"'.format(w)
                    for w in ["starttime", "endtime", "bbox", "identifier"]
                ))
                output_fobj.write("\r\n")
                initialize = False

            start = False
            previoustime = 0

            for row in izip(*data.itervalues()):

                if not start:
                    start = row[0]
                    dif = timedelta(seconds=1)
                else:
                    dif = row[0]-previoustime

                if dif != timedelta(seconds=1):
                    output_fobj.write(
                        ','.join('"{0}"'.format(w) for w in [
                            (start.isoformat("T") + "Z"),
                            (previoustime.isoformat("T") + "Z"),
                            "(0,0,0,0)", collection_id
                        ])
                    )
                    output_fobj.write("\r\n")
                    start = row[0]

                previoustime = row[0]

            # Write last "saved" time into response if product contained data,
            # meaning start is not a boolean
            if start:
                output_fobj.write(
                    ','.join('"{0}"'.format(w) for w in [
                        (start.isoformat("T") + "Z"),
                        (previoustime.isoformat("T") + "Z"),
                        "(0,0,0,0)", collection_id
                    ])
                )
                output_fobj.write("\r\n")


        return CDFileWrapper(output_fobj, **output)

    def handle(self, product, fields, low, high, step):
        """ Single product retrieval. """

        # read initial subset of the CDF data
        cdf_type = {}
        data = OrderedDict()

        with cdf_open(connect(product.data_items.all()[0])) as cdf:
            for field in fields:
                cdf_var = cdf.raw_var(field)
                cdf_type[field] = cdf_var.type()

                if "Bubble_Probability" in fields:
                    step = 1

                data[field] = cdf_var[low:high:step]


            # Some tests filtering out data not flagged with bubble index
            if "Bubble_Probability" in fields:
                # initialize indices
                index = arange(len(data['Bubble_Probability']))
                # filter the indices
                index = index[data["Bubble_Probability"][index] >= 0.1]
                # data update
                data = OrderedDict(
                    (field, values[index]) for field, values in data.iteritems()
                )

        return data, len(data['Timestamp']), cdf_type
