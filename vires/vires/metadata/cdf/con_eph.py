#-------------------------------------------------------------------------------
#
# Metadata extraction - CDF reader for multi-mission CON_EPH_2_ products
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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
# pylint: disable=missing-module-docstring

from math import ceil
from collections import namedtuple
from itertools import chain
from .base import CDFMetadataReader
from ...time_cdf import cdf_rawtime_delta_in_seconds


class ConEphCdfMetadataReader(CDFMetadataReader):
    """ Metadata reader for multi-mission conjunctions CON_EPH_2_ products
    """
    TYPE = "CDF-CON_EPH_2_"

    CROSSOVER_TIME_1_VARIABLE = "crossover_time_1"
    CROSSOVER_TIME_2_VARIABLE = "crossover_time_2"
    PLANE_ALIGNMENT_TIME_VARIABLE = "plane_alignment_time"

    TimeRange = namedtuple("TimeRange", ["start", "end"])

    @classmethod
    def read_cdf_metadata(cls, cdf, **options):
        del options

        time_range = cls.get_time_range(cdf)

        return {
            "format": cls.TYPE,
            "begin_time": time_range.start,
            "end_time": time_range.end,
            "max_record_duration": cls.read_max_record_duration(cdf)
        }

    @classmethod
    def read_max_record_duration(cls, cdf):
        """ Read maximum record duration of the crossover interval records. """
        max_record_duration = cdf_rawtime_delta_in_seconds(
            cdf.raw_var(cls.CROSSOVER_TIME_2_VARIABLE)[...],
            cdf.raw_var(cls.CROSSOVER_TIME_1_VARIABLE)[...],
            cdf.raw_var(cls.CROSSOVER_TIME_1_VARIABLE).type(),
        ).max()
        return {
            "crossover": f"PT{int(ceil(max_record_duration))}S",
        }

    @classmethod
    def get_time_range(cls, cdf):
        """ Get product time-range. """

        time_ranges = chain(
            cls._get_interval_time_range(
                cdf, cls.CROSSOVER_TIME_1_VARIABLE, cls.CROSSOVER_TIME_2_VARIABLE,
            ),
            cls._get_instant_time_range(
                cdf, cls.PLANE_ALIGNMENT_TIME_VARIABLE,
            ),
        )

        try:
            time_range = next(time_ranges)
        except StopIteration:
            raise ValueError(
                "Failed to extract time-range. Product contains no data."
            ) from None

        for next_time_range in time_ranges:
            time_range = cls.TimeRange(
                min(time_range.start, next_time_range.start),
                max(time_range.end, next_time_range.end),
            )

        return time_range

    @classmethod
    def _get_interval_time_range(cls, cdf, start_time_variable, end_time_variable):
        """ Yield interval time-range extracted from two time variables. """
        try:
            start_time_var = cdf.raw_var(start_time_variable)
            end_time_var = cdf.raw_var(end_time_variable)
        except KeyError as key:
            raise KeyError(f"Temporal variable {key} not found!") from None

        if start_time_var.shape != end_time_var.shape:
            raise ValueError("Shape mismatch between the start and end times!")

        start_times = start_time_var[...]
        end_times = end_time_var[...]

        if (start_times > end_times).any():
            raise ValueError("Start times after end times detected!")

        if start_times.size > 0:
            yield cls.TimeRange(
                cls._cdf_rawtime_to_datetime(start_times.min(), start_time_var.type()),
                cls._cdf_rawtime_to_datetime(end_times.max(), end_time_var.type()),
            )

    @classmethod
    def _get_instant_time_range(cls, cdf, time_variable):
        """ Get interval time-range extracted from a single variable. """
        try:
            time_var = cdf.raw_var(time_variable)
        except KeyError as key:
            raise KeyError(f"Temporal variable {key} not found!") from None

        times = time_var[...]

        if times.size > 0:
            yield cls.TimeRange(
                cls._cdf_rawtime_to_datetime(times.min(), time_var.type()),
                cls._cdf_rawtime_to_datetime(times.max(), time_var.type()),
            )
