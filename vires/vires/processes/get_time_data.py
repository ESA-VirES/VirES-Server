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
# pylint: disable=too-many-arguments,too-many-locals

import csv
from datetime import datetime, timedelta
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, CDTextBuffer, FormatText, RequestParameter,
    AllowedRange,
)
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.models import ProductCollection
from vires.access_util import get_vires_permissions
from vires.time_util import naive_to_utc, format_datetime, parse_duration
from vires.processes.base import WPSProcess
from vires.processes.util.time_series import MultiCollectionProductSource


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
        ("duration_threshold", LiteralData(
            "duration_threshold", timedelta, optional=True, default=None,
            allowed_values=AllowedRange(timedelta(0), None, dtype=timedelta),
            title="Minimum duration threshold for the selected products.",
            abstract=(
                "Products whose duration is below this threshold are rejected."
                "The default threshold is below the product nominal sampling."
            )
        )),
    ]

    outputs = {
        "times": ComplexData(
            "times", formats=[FormatText('text/csv')],
            title="Comma separated list of products, their extents and times.",
        )
    }

    def execute(self, permissions, collection_id, begin_time, end_time,
                duration_threshold, **kwargs):
        """ The main execution function for the process.
        """
        access_logger = self.get_access_logger(**kwargs)

        try:
            collections = [
                ProductCollection.select_permitted(permissions).get(identifier=id_)
                for id_ in collection_id.split("+")
            ]
        except ProductCollection.DoesNotExist:
            raise InvalidInputValueError(
                "collection", f"Invalid collection name {collection_id!r}!"
            ) from None

        # per-collection duration threshold
        duration_threshold = [
            (
                parse_duration(collection.metadata.get("nominalSampling", "PT0S"))
                if duration_threshold is None else duration_threshold
            )
            for collection in collections
        ]

        if begin_time:
            begin_time = naive_to_utc(begin_time)

        if end_time:
            end_time = naive_to_utc(end_time)

        access_logger.info(
            "request: collection: %s, toi: (%s, %s)",
            collection_id,
            format_datetime(naive_to_utc(begin_time)) if begin_time else "-",
            format_datetime(naive_to_utc(end_time)) if end_time else "-",
        )

        source = MultiCollectionProductSource(collections)

        output = CDTextBuffer()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(["starttime", "endtime", "bbox", "identifier"])

        envelope = "(-90,-180,90,180)"

        for index, start, end, id_ in source.iter_ids(begin_time, end_time):
            if end - start >= duration_threshold[index]:
                writer.writerow([
                    format_datetime(start), format_datetime(end), envelope, id_
                ])

        return output
