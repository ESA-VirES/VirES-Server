#-------------------------------------------------------------------------------
#
# Products management - product registration
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
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
# pylint: disable=missing-docstring

from vires.time_util import naive_to_utc
from vires.cdf_util import cdf_rawtime_to_datetime


class SwarmProductMetadataReader():

    TIME_VARIABLES = ["Timestamp", "timestamp", "Epoch", "t"]

    @classmethod
    def get_time_range_and_size(cls, cdf):
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
            naive_to_utc(cdf_rawtime_to_datetime(times[0], times.type())),
            naive_to_utc(cdf_rawtime_to_datetime(times[-1], times.type())),
            times.shape[0]
        )

    @classmethod
    def read(cls, data):
        begin_time, end_time, n_times = cls.get_time_range_and_size(data)

        return {
            "format": "CDF-Swarm",
            "size": (n_times, 0),
            "begin_time": begin_time,
            "end_time": end_time,
        }
