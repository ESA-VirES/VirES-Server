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
# pylint: disable=missing-docstring, too-many-locals, too-few-public-methods

from datetime import datetime
from itertools import izip
from cStringIO import StringIO
from numpy import amax, amin, vectorize, choose
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, CDFileWrapper,
)
from vires.aux import query_dst, query_kp
from vires.time_util import (
    mjd2000_to_datetime, mjd2000_to_unix_epoch, naive_to_utc,
)
from vires.processes.base import WPSProcess


def abs_amax(arr, axis):
    """ Get the elements with largest absolute values along the given axis."""
    arr_min = amin(arr, axis)
    arr_max = amax(arr, axis)
    return choose(abs(arr_max) > abs(arr_min), (arr_min, arr_max))


# Auxiliary data query function and file sources
AUX_INDEX = {
    "kp": (query_kp, settings.VIRES_AUX_DB_KP, amax, "%d"),
    "dst": (query_dst, settings.VIRES_AUX_DB_DST, abs_amax, "%.6g"),
}


class GetIndices(WPSProcess):
    """Retrieve auxiliary indices within the given time interval.
    Empty response is returned if there is no value matched.
    """
    identifier = "get_indices"
    title = "Auxiliary index retrieval."
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("index_id", LiteralData(
            'index_id', str, optional=False,
            abstract="Identifier of the queried auxiliary index.",
            allowed_values=('kp', 'dst'),
        )),
        ("begin_time", LiteralData(
            'begin_time', datetime, optional=False,
            abstract="Start of the requested time interval",
        )),
        ("end_time", LiteralData(
            'end_time', datetime, optional=False,
            abstract="End of the requested time interval",
        )),
        ("csv_time_format", LiteralData(
            'csv_time_format', str, optional=True, title="CSV time  format",
            abstract="Optional time format used by the CSV output.",
            allowed_values=("ISO date-time", "MJD2000", "Unix epoch"),
            default="ISO date-time",
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Requested subset of data", abstract=(
                "Process returns subset of data defined by time, bbox "
                "and collections."
            ), formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def execute(self, index_id, begin_time, end_time, csv_time_format,
                output, **kwarg):
        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)

        self.access_logger.info(
            "request: index: %s, toi: (%s, %s)",
            index_id, begin_time.isoformat("T"), end_time.isoformat("T"),
        )

        query, filename, lessen, data_format = AUX_INDEX[index_id]
        aux_data = query(filename, begin_time, end_time)

        time = aux_data["time"]
        data = aux_data[index_id]

        if time.size > 500:
            bin_size = (time.size - 1)//500 + 1
            bin_count = time.size // bin_size
            size = bin_size * bin_count
            shape = (bin_count, bin_size)
            data = lessen(data[:size].reshape(shape), 1)
            time = time[:size].reshape(shape)
            time = 0.5 * (time[:, 0] + time[:, -1])

        self.access_logger.info(
            "response: index: %s, count: %s values, mime-type: %s",
            index_id, len(time), output['mime_type'],
        )

        if csv_time_format == "ISO date-time":
            time_format = "%s"
            time = vectorize(mjd2000_to_datetime, otypes=(object,))(time)
        elif csv_time_format == "Unix epoch":
            time_format = "%.14g"
            time = mjd2000_to_unix_epoch(time)
        else: # csv_time_format == "MJD2000"
            time_format = "%.14g"

        line_format = "%s,%s,%s\r\n"
        row_format = line_format % (index_id, data_format, time_format)

        output_fobj = StringIO()
        output_fobj.write(line_format % ("id", "value", "time"))
        for row in izip(data, time):
            output_fobj.write(row_format % row)

        return CDFileWrapper(output_fobj, **output)
