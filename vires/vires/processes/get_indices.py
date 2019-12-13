#-------------------------------------------------------------------------------
#
# WPS fetch index data subset for time-slider visualisation
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
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
# pylint: disable=missing-docstring,too-many-locals,too-few-public-methods
# pylint: disable=too-many-arguments,unused-argument


from datetime import datetime
from itertools import izip
from cStringIO import StringIO
from numpy import amax, amin, vectorize, choose
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, CDFileWrapper,
)
from vires.aux_kp import KpReader
from vires.aux_dst import DstReader
from vires.aux_f107 import F10_2_Reader
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
    "kp": (
        KpReader(settings.VIRES_AUX_DB_KP), ("time", "kp"), amax, "%.1f"
    ),
    "dst": (
        DstReader(settings.VIRES_AUX_DB_DST), ("time", "dst"), abs_amax, "%.6g"
    ),
    "f107": (
        F10_2_Reader(settings.VIRES_CACHED_PRODUCTS["AUX_F10_2_"]),
        ("MJD2000", "F10.7"), amax, "%.6g"
    ),
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
            allowed_values=('kp', 'dst', 'f107'),
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

        reader, fields, lessen, data_format = AUX_INDEX[index_id]

        time, data = self._read_data(reader, begin_time, end_time, fields=fields)
        time, data = self._reduce_data(time, data, lessen)
        time, time_format = self._convert_time(time, csv_time_format)

        if index_id == 'kp':
            data = self._kp10_to_kp(data)

        output_fobj = self._write_csv(
            StringIO(), index_id, time, data, time_format, data_format
        )

        self.access_logger.info(
            "response: index: %s, count: %s values, mime-type: %s",
            index_id, len(time), output['mime_type'],
        )

        return CDFileWrapper(output_fobj, **output)

    @staticmethod
    def _kp10_to_kp(kp10):
        return 0.1 * kp10

    @staticmethod
    def _read_data(reader, begin_time, end_time, fields):
        aux_data = reader.subset(begin_time, end_time, fields=fields)
        return [aux_data[field] for field in fields]

    @staticmethod
    def _reduce_data(time, data, lessen, max_count=500):
        if time.size > max_count:
            bin_size = (time.size - 1)//max_count + 1
            bin_count = time.size // bin_size
            size = bin_size * bin_count
            shape = (bin_count, bin_size)
            data = lessen(data[:size].reshape(shape), 1)
            time = time[:size].reshape(shape)
            time = 0.5 * (time[:, 0] + time[:, -1])
        return time, data

    @staticmethod
    def _convert_time(time, csv_time_format):
        if csv_time_format == "ISO date-time":
            time_format = "%s"
            time = vectorize(mjd2000_to_datetime, otypes=(object,))(time)
        elif csv_time_format == "Unix epoch":
            time_format = "%.14g"
            time = mjd2000_to_unix_epoch(time)
        else: # csv_time_format == "MJD2000"
            time_format = "%.14g"
        return time, time_format

    @staticmethod
    def _write_csv(file_out, index_id, time, data, time_format, data_format):
        line_format = "%s,%s,%s\r\n"
        row_format = line_format % (index_id, data_format, time_format)
        file_out.write(line_format % ("id", "value", "time"))
        for row in izip(data, time):
            file_out.write(row_format % row)
        return file_out
