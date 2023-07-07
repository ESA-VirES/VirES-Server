#-------------------------------------------------------------------------------
#
# Products management - product registration
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
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
# pylint: disable=missing-docstring,too-few-public-methods

from vires.time_util import naive_to_utc
from vires.cdf_util import cdf_rawtime_to_datetime


class CDFReader:
    @staticmethod
    def _cdf_rawtime_to_datetime(time, cdf_type):
        return naive_to_utc(cdf_rawtime_to_datetime(time, cdf_type))


class SwarmProductMetadataReader(CDFReader):

    TIME_EXTENT_ATTRIBUTE = "TIME_EXTENT"

    TIME_VARIABLES = [
        "Timestamp",
        "timestamp",
        "Epoch",
        "t",
    ]

    @classmethod
    def _read_time_extent(cls, attr):
        attr._raw = True # pylint: disable=protected-access
        cdf_type = attr.type(0)
        begin_time, end_time = attr[0]
        return (
            cls._cdf_rawtime_to_datetime(begin_time, cdf_type),
            cls._cdf_rawtime_to_datetime(end_time, cdf_type),
        )

    @classmethod
    def get_time_range(cls, cdf):

        try:
            return cls._read_time_extent(cdf.attrs[cls.TIME_EXTENT_ATTRIBUTE])
        except (KeyError, IndexError, ValueError):
            pass # fallback to extraction from the Timestamp array

        # iterate possible time keys and try to extract the values
        for time_variable in cls.TIME_VARIABLES:
            try:
                times = cdf.raw_var(time_variable)
            except KeyError:
                continue
            else:
                break
        else:
            raise KeyError("Temporal variable not found!")

        if len(times.shape) != 1:
            raise ValueError("Incorrect dimension of the time-stamp array!")

        return (
            cls._cdf_rawtime_to_datetime(times[0], times.type()),
            cls._cdf_rawtime_to_datetime(times[-1], times.type()),
        )

    @classmethod
    def read(cls, data):
        begin_time, end_time = cls.get_time_range(data)

        return {
            "format": "CDF-Swarm",
            "begin_time": begin_time,
            "end_time": end_time,
        }


class ObsProductMetadataReader(CDFReader):

    TIME_VARIABLE = "Timestamp"
    SITE_CODES_ATTR = "IAGA_CODES"
    INDEX_RANGES_ATTR = "INDEX_RANGES"

    @classmethod
    def read_times(cls, cdf, time_variable):
        try:
            time_var = cdf.raw_var(time_variable)
        except KeyError:
            time_var = None
        else:
            cdf_type = time_var.type()
            times = time_var[...]

        if time_var is None:
            raise KeyError("Temporal variable not found!")

        if len(times.shape) != 1:
            raise ValueError("Incorrect dimension of the time-stamp array!")

        return times, cdf_type


    @classmethod
    def read_obs_index_ranges(cls, cdf, codes_attr_name, ranges_attr_name):
        return dict(zip(list(cdf.attrs[codes_attr_name]), [
            (int(start), int(stop))
            for start, stop in list(cdf.attrs[ranges_attr_name])
        ]))

    @classmethod
    def get_obs_info(cls, cdf):
        index_ranges = cls.read_obs_index_ranges(
            cdf, cls.SITE_CODES_ATTR, cls.INDEX_RANGES_ATTR,
        )
        times, cdf_type = cls.read_times(cdf, cls.TIME_VARIABLE)

        datasets = {
            code: {
                'index_range': (start, stop),
                'begin_time': cls._cdf_rawtime_to_datetime(times[start], cdf_type),
                'end_time': cls._cdf_rawtime_to_datetime(times[stop - 1], cdf_type),
            }
            for code, (start, stop) in index_ranges.items()

        }

        return (
            cls._cdf_rawtime_to_datetime(times.min(), cdf_type),
            cls._cdf_rawtime_to_datetime(times.max(), cdf_type),
            datasets,
        )

    @classmethod
    def read(cls, cdf):
        begin_time, end_time, datasets = cls.get_obs_info(cdf)

        return {
            "format": "CDF-OBS",
            "begin_time": begin_time,
            "end_time": end_time,
            "datasets": datasets,
        }


class VObsProductMetadataReader(ObsProductMetadataReader):
    TIME_VARIABLE_SV = "Timestamp_SV"
    SITE_CODES_ATTR = "SITE_CODES"
    INDEX_RANGES_ATTR = "INDEX_RANGES"
    INDEX_RANGES_SV_ATTR = "INDEX_RANGES_SV"
    SV_DATASET = "SecularVariation"

    @classmethod
    def get_obs_info(cls, cdf):
        index_ranges = cls.read_obs_index_ranges(
            cdf, cls.SITE_CODES_ATTR, cls.INDEX_RANGES_ATTR,
        )
        index_ranges_sv = cls.read_obs_index_ranges(
            cdf, cls.SITE_CODES_ATTR, cls.INDEX_RANGES_SV_ATTR,
        )
        times, cdf_type = cls.read_times(cdf, cls.TIME_VARIABLE)
        times_sv, _ = cls.read_times(cdf, cls.TIME_VARIABLE_SV)

        datasets = {
            **{
                code: {
                    'index_range': (start, stop),
                    'begin_time': cls._cdf_rawtime_to_datetime(times[start], cdf_type),
                    'end_time': cls._cdf_rawtime_to_datetime(times[stop - 1], cdf_type),
                }
                for code, (start, stop) in index_ranges.items()
            },
            **{
                f'{cls.SV_DATASET}:{code}': {
                    'index_range': (start, stop),
                    'begin_time': cls._cdf_rawtime_to_datetime(times_sv[start], cdf_type),
                    'end_time': cls._cdf_rawtime_to_datetime(times_sv[stop - 1], cdf_type),
                }
                for code, (start, stop) in index_ranges_sv.items()
            },
        }

        return (
            cls._cdf_rawtime_to_datetime(times.min(), cdf_type),
            cls._cdf_rawtime_to_datetime(times.max(), cdf_type),
            datasets,
        )
