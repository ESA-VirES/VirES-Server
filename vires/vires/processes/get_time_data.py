#-------------------------------------------------------------------------------
#
# getTimeData process ported from EOxServer
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=too-few-public-methods,unused-argument

import csv
from datetime import datetime
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, CDTextBuffer, FormatText, RequestParameter,
)
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.models import ProductCollection
from vires.access_util import get_vires_permissions
from vires.time_util import naive_to_utc, format_datetime
from vires.processes.base import WPSProcess


class GetTimeDataProcess(WPSProcess):
    """ Simple catalogue-like query WPS process. """
    identifier = "getTimeData"
    title = "Get times of collection coverages."
    decription = (
        "Query collection and get list of coverages and their times "
        "and spatial extents. The process is used by the time-slider "
        "of the EOxClient (web client)."
    )

    metadata = {}
    profiles = ['EOxServer:GetTimeData']

    inputs = WPSProcess.inputs + [
        ("permissions", RequestParameter(get_vires_permissions)),
        ("collection_id", LiteralData(
            "collection",
            title="Collection name."
        )),
        ("begin_time", LiteralData(
            "begin_time", datetime, optional=True,
            title="Optional start of the queried time interval."
        )),
        ("end_time", LiteralData(
            "end_time", datetime, optional=True,
            title="Optional end of the queried time interval."
        )),
    ]

    outputs = {
        "times": ComplexData(
            "times", formats=[FormatText('text/csv')],
            title="Comma separated list of products, their extents and times.",
        )
    }

    def execute(self, permissions, collection_id, begin_time, end_time, **kwargs):
        """ The main execution function for the process.
        """
        access_logger = self.get_access_logger(**kwargs)

        try:
            collection = ProductCollection.select_permitted(permissions).get(
                identifier=collection_id
            )
        except ProductCollection.DoesNotExist:
            raise InvalidInputValueError(
                "collection", "Invalid collection name '%s'!" % collection_id
            )

        access_logger.info(
            "request: collection: %s, toi: (%s, %s)",
            collection_id,
            format_datetime(naive_to_utc(begin_time)) if begin_time else "-",
            format_datetime(naive_to_utc(end_time)) if end_time else "-",
        )

        query = collection.products.order_by('begin_time')
        if end_time:
            query = query.filter(begin_time__lte=naive_to_utc(end_time))
        if begin_time:
            query = query.filter(
                end_time__gte=naive_to_utc(begin_time),
                begin_time__gte=(begin_time - collection.max_product_duration),
            )
        query = query.values_list("begin_time", "end_time", "identifier")

        output = CDTextBuffer()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(["starttime", "endtime", "bbox", "identifier"])

        envelope = "(-90,-180,90,180)"

        for start, end, id_ in query:
            writer.writerow([
                format_datetime(start), format_datetime(end), envelope, id_
            ])

        return output
