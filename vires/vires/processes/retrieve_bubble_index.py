#-------------------------------------------------------------------------------
#
# WPS process fetching plasma bubbles time intervals.
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
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
# pylint: disable=no-self-use,unused-argument


import csv
from datetime import datetime
from numpy import concatenate
from eoxserver.core.util.timetools import isoformat
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, CDTextBuffer, FormatText
)
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.models import ProductCollection
from vires.time_util import naive_to_utc
from vires.cdf_util import cdf_rawtime_to_datetime
from vires.processes.base import WPSProcess
from vires.processes.util.time_series import ProductTimeSeries

TIME_VARIABLE = "Timestamp"
DATA_VARIABLE = "Bubble_Probability"
BUBBLE_PROBABILITY_THRESHOLD = 0.1


class RetrieveBubbleIndex(WPSProcess):
    """ Process for retrieving information of time-spans covered by bubbles.
    """
    identifier = "retrieve_bubble_index"
    title = "Retrieve filtered Swarm data."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("collection_id", LiteralData(
            'collection', str, optional=False,
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
            'times', title="Output data",
            formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def execute(self, collection_id, begin_time, end_time, output, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        try:
            time_series = ProductTimeSeries(
                ProductCollection.objects
                .select_related('type')
                .filter(type__identifier="SW_IBIxTMS_2F")
                .get(identifier=collection_id)
            )
        except ProductCollection.DoesNotExist:
            raise InvalidInputValueError(
                "collection_id",
                "Invalid collection identifier %r!" % collection_id
            )

        access_logger.info(
            "request: collection: %s, toi: (%s, %s)",
            collection_id,
            naive_to_utc(begin_time).isoformat("T") if begin_time else "-",
            naive_to_utc(end_time).isoformat("T") if end_time else "-",
        )

        def _generate_pairs():
            variables = [TIME_VARIABLE, DATA_VARIABLE]
            for dataset in time_series.subset(begin_time, end_time, variables):
                if dataset.length == 0:
                    continue
                cdf_type = dataset.cdf_type[TIME_VARIABLE]
                time = dataset[TIME_VARIABLE]
                data = dataset[DATA_VARIABLE]

                flag = (data > BUBBLE_PROBABILITY_THRESHOLD).astype('int')
                change = flag[1:] - flag[:-1]
                starts = (change == +1).nonzero()[0] + 1
                ends = (change == -1).nonzero()[0]

                if flag[0] == 1:
                    starts = concatenate(([0], starts))
                if flag[-1] == 1:
                    ends = concatenate((ends, [flag.size - 1]))

                for start, end in zip(starts, ends):
                    yield (
                        cdf_rawtime_to_datetime(time[start], cdf_type),
                        cdf_rawtime_to_datetime(time[end], cdf_type),
                        dataset.source
                    )

        output = CDTextBuffer()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(["starttime", "endtime", "bbox", "identifier"])

        envelope = "(-90,-180,90,180)"

        for start, end, id_ in _generate_pairs():
            writer.writerow([isoformat(start), isoformat(end), envelope, id_])

        return output
