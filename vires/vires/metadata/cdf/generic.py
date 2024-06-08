#-------------------------------------------------------------------------------
#
# Products metadata extraction - generic CDF metadata reader
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2014-2024 EOX IT Services GmbH
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


class GenericCdfMetadataReader(CDFMetadataReader):
    """ Metadata reader for generic CDF files.
    Works for Swarm and Swarm-like products.
    """
    TYPE = "CDF-generic"
    TIME_EXTENT_ATTRIBUTE = "TIME_EXTENT"

    @classmethod
    def extract_options(cls, product_type):
        """ find primary time variable """
        dataset_definition = product_type.get_dataset_definition(None)
        primary_time_variables = (
            properties.get("source", name)
            for name, properties in dataset_definition.items()
            if properties.get("primaryTimestamp")
        )
        for time_variable in primary_time_variables:
            return {"time_variable": time_variable}
        raise ValueError(
            f"Failed to find primary time variable of {product_type.identifier}!"
        )

    @classmethod
    def read_cdf_metadata(cls, cdf, **options):
        begin_time, end_time = cls.get_time_range(cdf, options["time_variable"])
        return {
            "format": cls.TYPE,
            "begin_time": begin_time,
            "end_time": end_time,
        }

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
    def get_time_range(cls, cdf, time_variable):

        try:
            return cls._read_time_extent(cdf.attrs[cls.TIME_EXTENT_ATTRIBUTE])
        except (KeyError, IndexError, ValueError):
            pass # fallback to extraction from the Timestamp array

        try:
            times = cdf.raw_var(time_variable)
        except KeyError:
            raise KeyError(f"Temporal variable {time_variable} not found!") from None

        if len(times.shape) != 1:
            raise ValueError("Incorrect dimension of the time-stamp array!")

        return (
            cls._cdf_rawtime_to_datetime(times[0], times.type()),
            cls._cdf_rawtime_to_datetime(times[-1], times.type()),
        )
