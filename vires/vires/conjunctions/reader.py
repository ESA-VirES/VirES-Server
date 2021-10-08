#-------------------------------------------------------------------------------
#
# Conjunction table subset reader
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments,too-few-public-methods,

from numpy import abs as aabs, asarray, searchsorted, timedelta64
from vires.cdf_util import cdf_open
from vires.time_util import datetime_to_datetime64, datetime64_to_datetime
from vires.cdf_write_util import CdfTypeEpoch
from vires.cdf_data_reader import read_cdf_time_series, sorted_range_slice

TD_1_MS = timedelta64(1, 'ms')


def read_conjunctions(filename, start_time, end_time, max_angular_separation=1.0):
    """ Read conjunctions from the conjunctions table. """
    start_time = datetime_to_datetime64(start_time, 'ms') if start_time else None
    end_time = datetime_to_datetime64(end_time, 'ms') if end_time else None

    with cdf_open(filename) as cdf:
        dataset = read_cdf_time_series(
            cdf, ["Timestamp", "AngularSeparation"],
            time_slice=sorted_range_slice(
                start_time, end_time, right_closed=True
            )
        )
        sources, start_time, end_time = _read_sources(cdf, start_time, end_time)

    # filter values
    dataset = dataset.subset(
        dataset['AngularSeparation'] <= max_angular_separation
    )

    # the actual time-extent of the extracted data replacing the None inputs
    start_time = datetime64_to_datetime(start_time)
    end_time = datetime64_to_datetime(end_time)

    return dataset, sources, start_time, end_time


def _read_sources(cdf, start, end):

    def _read_time_ranges(attr):
        attr._raw = True               # pylint: disable=protected-access
        return CdfTypeEpoch.decode(asarray(list(attr)))

    def _add_overlap(starts, ends, distance, overlap):
        idx, = (aabs((starts - ends) - distance) < TD_1_MS).nonzero()
        ends[idx] += overlap
        starts[idx] -= overlap

    def _find_subset(starts, ends, start, end, margin=0, offset=0):
        return (
            max(0, searchsorted(ends, start, 'left') - margin) + offset,
            searchsorted(starts, end, 'left') + margin + offset
        )

    neighbour_distance = timedelta64(int(cdf.attrs['NEIGHBOUR_DISTANCE'][0]), 'ms')
    neighbour_overlap = timedelta64(int(cdf.attrs['NEIGHBOUR_OVERLAP'][0]), 'ms')
    ranges = _read_time_ranges(cdf.attrs['SOURCE_TIME_RANGES'])

    if ranges.size == 0:
        return []

    start = start or ranges[0, 0]
    end = end or ranges[-1, 1]

    # find first rough subset with margin
    idx_start, idx_stop = _find_subset(
        ranges[:, 0], ranges[:, 1], start, end, margin=1
    )
    ranges_subset = ranges[idx_start:idx_stop, :]

    # add the temporal overlaps
    _add_overlap(
        ranges_subset[1:, 0], ranges_subset[:-1, 1],
        neighbour_distance, neighbour_overlap
    )

    # find the final exact subset
    idx_start, idx_stop = _find_subset(
        ranges_subset[:, 0], ranges_subset[:, 1], start, end,
        offset=idx_start
    )

    return [
        source
        for line in cdf.attrs['SOURCES'][idx_start:idx_stop]
        for source in line.split()
    ], start, end
