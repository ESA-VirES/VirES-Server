#-------------------------------------------------------------------------------
#
# Products metadata extraction - CDF reader for ground observatory products
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020-2024 EOX IT Services GmbH
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
# pylint: disable=missing-docstring

from .base import CDFMetadataReader


class ObsCdfMetadataReader(CDFMetadataReader):
    """ Metadata reader for Swarm auxiliary ground observatory CDF products.
    """
    TYPE = "CDF-OBS"

    TIME_VARIABLE = "Timestamp"
    LOCATION_VARIABLES = {
        "latitude": "Latitude",
        "longitude": "Longitude",
        "radius": "Radius",
    }
    SITE_CODES_ATTR = "IAGA_CODES"
    INDEX_RANGES_ATTR = "INDEX_RANGES"

    @classmethod
    def read_cdf_metadata(cls, cdf, **options):
        del options

        begin_time, end_time, datasets = cls.get_obs_info(cdf)

        return {
            "format": cls.TYPE,
            "begin_time": begin_time,
            "end_time": end_time,
            "datasets": datasets,
        }

    @classmethod
    def get_obs_info(cls, cdf):
        index_ranges = cls.read_obs_index_ranges(
            cdf, cls.SITE_CODES_ATTR, cls.INDEX_RANGES_ATTR,
        )
        times, cdf_type = cls.read_times(cdf, cls.TIME_VARIABLE)
        locations = {
            key: cls.read_values(cdf, variable)
            for key, variable in cls.LOCATION_VARIABLES.items()
        }

        datasets = {
            code: {
                "index_range": (start, stop),
                "begin_time": cls._cdf_rawtime_to_datetime(times[start], cdf_type),
                "end_time": cls._cdf_rawtime_to_datetime(times[stop - 1], cdf_type),
                "location": {
                    "crs": "ITRF",
                    **{key: values[start] for key, values in locations.items()},
                }
            }
            for code, (start, stop) in index_ranges.items()

        }

        return (
            cls._cdf_rawtime_to_datetime(times.min(), cdf_type),
            cls._cdf_rawtime_to_datetime(times.max(), cdf_type),
            datasets,
        )

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
    def read_values(cls, cdf, variable):
        try:
            return cdf.raw_var(variable)
        except KeyError:
            raise KeyError(f"{variable} variable not found!") from None

    @classmethod
    def read_obs_index_ranges(cls, cdf, codes_attr_name, ranges_attr_name):
        return dict(zip(list(cdf.attrs[codes_attr_name]), [
            (int(start), int(stop))
            for start, stop in list(cdf.attrs[ranges_attr_name])
        ]))
