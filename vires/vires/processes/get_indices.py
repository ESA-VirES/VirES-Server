#-------------------------------------------------------------------------------
#
# WPS fetch index data subset for time-slider visualisation
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2014-2023 EOX IT Services GmbH
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
# pylint: disable=too-many-locals,too-few-public-methods
# pylint: disable=too-many-arguments,unused-argument


from datetime import datetime
from io import StringIO
from numpy import vectorize, choose, ravel, stack, concatenate
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, CDFileWrapper,
)
from vires.aux_f107 import F10_2_Reader
from vires.time_util import (
    mjd2000_to_datetime, mjd2000_to_unix_epoch, naive_to_utc,
    format_datetime,
)
from vires.cdf_util import cdf_rawtime_to_mjd2000
from vires.processes.base import WPSProcess
from vires.processes.util.time_series import get_product_time_series
from vires.cache_util import cache_path
from vires.data.vires_settings import CACHED_PRODUCT_FILE


class BaseReader:
    """ Base data reader. """
    data_format = None
    fields = (None, None)

    @classmethod
    def lessen(cls, array, axis):
        """ Data reduction, get largest value along the given axis. """
        return cls._amax(array, axis)

    @classmethod
    def reduce_data(cls, time, data, max_count=500):
        """ Reduce size of the data. """
        return cls._reduce_data(time, data, max_count=max_count)

    @classmethod
    def read_data(cls, start, end):
        """ Read data matched by the given time-selection. """
        raise NotImplementedError

    @classmethod
    def read_reduced_data(cls, start, end, max_count=500):
        """ Read reduced-size data matched by the given time-selection. """
        time, data = cls.read_data(start, end)
        return cls.reduce_data(time, data, max_count=max_count)

    @staticmethod
    def _amax(array, axis):
        """ Get largest value along the given axis. """
        return array.max(axis)

    @staticmethod
    def _abs_amax(array, axis):
        """ Get the elements with largest absolute values along the given axis. """
        array_min = array.min(axis)
        array_max = array.max(axis)
        return choose(abs(array_max) > abs(array_min), (array_min, array_max))

    @classmethod
    def _reduce_data(cls, time, data, max_count):
        if time.size > max_count:
            bin_size = (time.size - 1)//max_count + 1
            bin_count = time.size // bin_size
            size = bin_size * bin_count
            shape = (bin_count, bin_size)
            data = cls.lessen(data[:size].reshape(shape), 1)
            time = time[:size].reshape(shape)
            time = 0.5 * (time[:, 0] + time[:, -1])
        return time, data

    @classmethod
    def _reduce_stepwise_data(cls, time, data, max_count):
        n_steps = time.size - 1
        if n_steps > max_count:
            bin_size = (n_steps - 1)// max_count + 1
            bin_count = n_steps // bin_size
            shape = (bin_count, bin_size)
            size = bin_size * bin_count
            data = cls.lessen(data[:size].reshape(shape), 1)
            time = time[:(size + 1)]
            time = concatenate((time[:-1].reshape(shape)[:, 0], time[-1:]))
        time = ravel(stack((time[:-1], time[1:]), axis=-1))
        data = ravel(stack((data, data), axis=-1))
        return time, data


class F107Reader(BaseReader):
    """ F10.7 index reader """
    data_format = "%.6g"
    fields = ("MJD2000", "F10.7")

    @classmethod
    def read_data(cls, start, end):
        reader = cls._get_reader()
        data = reader.subset(start, end, fields=cls.fields)
        return tuple(data[field] for field in cls.fields)

    @classmethod
    def _get_reader(cls):
        return F10_2_Reader(cache_path(CACHED_PRODUCT_FILE["AUX_F10_2_"]))


class CollectionReader(BaseReader):
    """ Extraction of auxiliary indices from a regular times-series collection.
    """
    collection_id = None

    @classmethod
    def read_data(cls, start, end):
        time_field, data_field = cls.fields
        data = cls._read_data(start, end, (time_field, data_field))
        return (
            cdf_rawtime_to_mjd2000(data[time_field], data.cdf_type[time_field]),
            data[data_field]
        )

    @classmethod
    def _read_data(cls, start, end, fields):
        time_series = get_product_time_series(cls.collection_id)

        data_chunks = time_series.subset(
            start - 2 * time_series.segment_neighbourhood,
            end + 2 * time_series.segment_neighbourhood,
            variables=fields
        )

        try:
            data = next(data_chunks)
        except StopIteration:
            raise RuntimeError("No data chunk received!") from None

        for data_chunk in data_chunks:
            data.append(data_chunk)

        return data


class KpReader(CollectionReader):
    """ Kp index reader class """
    collection_id = "GFZ_KP"
    data_format = "%.1f"
    fields = ("Timestamp", "Kp")

    @classmethod
    def reduce_data(cls, time, data, max_count=500):
        return cls._reduce_stepwise_data(time, data, max_count=max_count)


class DstReader(CollectionReader):
    """ Dst index reader class """
    collection_id = "WDC_DST"
    data_format = "%.6g"
    fields = ("Timestamp", "Dst")

    @classmethod
    def lessen(cls, array, axis):
        return cls._abs_amax(array, axis)


class DDstReader(CollectionReader):
    """ dDst index reader class """
    collection_id = "WDC_DST"
    data_format = "%.6g"
    fields = ("Timestamp", "dDst")

    @classmethod
    def reduce_data(cls, time, data, max_count=500):
        return cls._reduce_stepwise_data(time, data, max_count=max_count)


class GetIndices(WPSProcess):
    """Retrieve auxiliary indices within the given time interval.
    Empty response is returned if there is no value matched.
    """

    DATA_READER = {
        "kp": KpReader,
        "dst": DstReader,
        "ddst": DDstReader,
        "f107": F107Reader,
    }

    identifier = "get_indices"
    title = "Auxiliary index retrieval."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("index_id", LiteralData(
            'index_id', str, optional=False,
            abstract="Identifier of the queried auxiliary index.",
            allowed_values=list(DATA_READER),
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
                output, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)

        access_logger.info(
            "request: index: %s, toi: (%s, %s)",
            index_id, format_datetime(begin_time), format_datetime(end_time),
        )

        reader = self.DATA_READER[index_id]

        time, data = reader.read_reduced_data(begin_time, end_time)

        time, time_format = self._convert_time(time, csv_time_format)

        output_fobj = StringIO(newline="\r\n")
        self._write_csv(
            output_fobj, index_id, time, data, time_format, reader.data_format
        )

        access_logger.info(
            "response: index: %s, count: %s values, mime-type: %s",
            index_id, len(time), output['mime_type'],
        )

        return CDFileWrapper(output_fobj, **output)

    @staticmethod
    def _convert_time(time, csv_time_format):
        if csv_time_format == "ISO date-time":
            time_format = "%s"
            time = vectorize(
                lambda t: format_datetime(naive_to_utc(mjd2000_to_datetime(t))),
            )(time)
        elif csv_time_format == "Unix epoch":
            time_format = "%.14g"
            time = mjd2000_to_unix_epoch(time)
        else: # csv_time_format == "MJD2000"
            time_format = "%.14g"
        return time, time_format

    @staticmethod
    def _write_csv(file_out, index_id, time, data, time_format, data_format):
        line_format = "%s,%s,%s"
        row_format = line_format % (index_id, data_format, time_format)
        print(line_format % ("id", "value", "time"), file=file_out)
        for row in zip(data, time):
            print(row_format % row, file=file_out)
