#-------------------------------------------------------------------------------
#
# Products metadata extraction - CDF reader for virtual observatory products
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

from .obs import ObsCdfMetadataReader


class VobsCdfMetadataReader(ObsCdfMetadataReader):
    """ Metadata reader for Swarm-like virtual observatory CDF products.
    """
    TYPE = "CDF-VOBS"

    TIME_VARIABLE_SV = "Timestamp_SV"
    LOCATION_VARIABLES_SV = {
        "latitude": "Latitude_SV",
        "longitude": "Longitude_SV",
        "radius": "Radius_SV",
    }
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
        locations = {
            key: cls.read_values(cdf, variable)
            for key, variable in cls.LOCATION_VARIABLES.items()
        }
        times_sv, _ = cls.read_times(cdf, cls.TIME_VARIABLE_SV)
        locations_sv = {
            key: cls.read_values(cdf, variable)
            for key, variable in cls.LOCATION_VARIABLES_SV.items()
        }

        datasets = {
            **{
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
            },
            **{
                f"{cls.SV_DATASET}:{code}": {
                    "index_range": (start, stop),
                    "begin_time": cls._cdf_rawtime_to_datetime(times_sv[start], cdf_type),
                    "end_time": cls._cdf_rawtime_to_datetime(times_sv[stop - 1], cdf_type),
                    "location": {
                        "crs": "ITRF",
                        **{key: values[start] for key, values in locations_sv.items()},
                    }
                }
                for code, (start, stop) in index_ranges_sv.items()
            },
        }

        return (
            cls._cdf_rawtime_to_datetime(times.min(), cdf_type),
            cls._cdf_rawtime_to_datetime(times.max(), cdf_type),
            datasets,
        )
