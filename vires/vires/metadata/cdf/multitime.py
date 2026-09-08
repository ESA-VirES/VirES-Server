#-------------------------------------------------------------------------------
#
# Products metadata extraction - CDF metadata reader for datasets with multiple
#                                timestamp variables
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

from vires.time_util import naive_to_utc
from .base import CDFMetadataReader
from ...time_cdf import DT_INVALID_VALUE

DT_INVALID_VALUE_UTC = naive_to_utc(DT_INVALID_VALUE)


class MultitimeCdfMetadataReader(CDFMetadataReader):
    """ Metadata reader for CDF files with multiple timestamp variables
    and no default/main dataset.
    The time-extent of a product is determined by extracting extent
    of each dataset time variable.
    Works for Swarm and Swarm-like products.
    """
    TYPE = "CDF-multitime"

    @classmethod
    def extract_options(cls, product_type):
        """ find primary time variable """

        def _get_primary_time_variables():
            datasets = product_type.definition['datasets']
            for dataset_name in datasets:
                dataset_definition = product_type.get_dataset_definition(dataset_name)
                for name, properties in dataset_definition.items():
                    if properties.get("primaryTimestamp"):
                        yield properties.get("source", name)

        if time_variables := list(_get_primary_time_variables()):
            return {"time_variables": time_variables}

        raise ValueError(
            f"Failed to find any primary time variable of {product_type.identifier}!"
        )


    @classmethod
    def read_cdf_metadata(cls, cdf, **options):
        begin_time, end_time = cls.get_max_time_range(cdf, options["time_variables"])
        return {
            "format": cls.TYPE,
            "begin_time": begin_time,
            "end_time": end_time,
        }

    @classmethod
    def get_max_time_range(cls, cdf, time_variables):

        def _update_time(current_time, update_time, compare_times):
            if current_time is None:
                return update_time
            if update_time is None:
                return current_time
            return compare_times(current_time, update_time)

        begin_time, end_time = None, None

        for variable in time_variables:
            next_begin_time, next_end_time = cls.get_time_range(cdf, variable)
            print(variable, next_begin_time, next_end_time)
            begin_time = _update_time(begin_time, next_begin_time, min)
            end_time = _update_time(end_time, next_end_time, max)

        if begin_time is None or end_time is None:
            raise ValueError("Failed to extract product time range!")

        print(" <== ", begin_time, end_time)

        return begin_time, end_time

    @classmethod
    def get_time_range(cls, cdf, time_variable):

        try:
            times = cdf.raw_var(time_variable)
        except KeyError:
            raise KeyError(f"Temporal variable {time_variable} not found!") from None

        if len(times.shape) != 1:
            raise ValueError("Incorrect dimension of the time-stamp array!")

        if times.shape[0] == 0:
            return None, None

        start = cls._cdf_rawtime_to_datetime(times[0], times.type())
        end = cls._cdf_rawtime_to_datetime(times[-1], times.type())

        if DT_INVALID_VALUE_UTC in (start, end):
            raise ValueError(f"Invalid temporal extent! {start}/{end}")

        return start, end
