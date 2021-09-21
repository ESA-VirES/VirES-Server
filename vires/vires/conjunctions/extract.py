#-------------------------------------------------------------------------------
#
# conjunctions - extraction from input data
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=

from collections import namedtuple
from numpy import (
    timedelta64, searchsorted,
    degrees, stack, ones, arccos,
    arange, sign,
)
from numpy.testing import assert_equal
from eoxmagmod import convert, GEOCENTRIC_CARTESIAN, GEOCENTRIC_SPHERICAL
from .util import OutputData

ONE_SEC = timedelta64(1, 's')
HALF_SEC = timedelta64(500, 'ms')


def extract_conjunctions(orbit1, orbit2):
    """ Extract minima in angular distance between spacecrafts. """

    def _extract_conjunctions(orbit1, orbit2):
        distances = OutputData(
            orbit1.times,
            get_angular_distance(orbit1, orbit2)
        )
        return distances[get_local_minima(distances.dists)]

    return OutputData.join(*[
        _extract_conjunctions(segment1, segment2)
        for segment1, segment2 in extract_overlapping_data(orbit1, orbit2)
    ])


class TimeRange(namedtuple('TimeRange', ['start', 'end'])):
    """ Time range auxiliary class. """

    @property
    def is_empty(self):
        """ True if the time range is empty. """
        return self.start >= self.end

    def trim_start(self, new_start):
        """ Replace the start time with the given time. """
        return TimeRange(new_start, self.end)


def get_angular_distance(orbit1, orbit2):
    """ Calculate angular distance in degrees from two spherical
    (latitude, longitude) coordinates in degrees.
    """
    xyz1 = convert(
        stack((orbit1.lats, orbit1.lons, ones(orbit1.lats.shape)), axis=-1),
        GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN
    )
    xyz2 = convert(
        stack((orbit2.lats, orbit2.lons, ones(orbit2.lats.shape)), axis=-1),
        GEOCENTRIC_SPHERICAL, GEOCENTRIC_CARTESIAN
    )
    return degrees(arccos((xyz1 * xyz2).sum(axis=-1)))


def get_local_minima(values):
    """ Find indices of the local minima of the given series. """

    def _find_min_ranges():
        slope_sign = sign(values[2:] - values[:-2])
        for idx0 in (slope_sign[:-1] < slope_sign[1:]).nonzero()[0]:
            if slope_sign[idx0] != -1:
                continue
            for idx1 in range(idx0 +1, len(slope_sign)):
                if slope_sign[idx1] != +1:
                    continue
                break
            else:
                break
            yield (idx0+1, idx1+2)

    def _find_min():
        index = arange(len(values))
        for idx0, idx1 in _find_min_ranges():
            yield index[idx0:idx1][values[idx0:idx1].argmin()]

    return list(_find_min())


def calculate_slope(times, values):
    " Calculate slopes per interval, equidistant sampling is assumed."
    return times[1:-1], 0.5*(values[2:] - values[:-2])


def extract_overlapping_data(orbit1, orbit2):
    """ Extract overlaping uninterupted data segments. """
    time_ranges1 = generate_time_ranges(orbit1.times)
    time_ranges2 = generate_time_ranges(orbit2.times)

    for time_range in generate_time_range_overlaps(time_ranges1, time_ranges2):
        slice1 = get_temporal_slice(orbit1.times, *time_range)
        slice2 = get_temporal_slice(orbit2.times, *time_range)
        assert_equal(orbit1.times[slice1], orbit2.times[slice2])
        yield orbit1[slice1], orbit2[slice2]


def get_temporal_slice(times, start_time, end_time):
    """ Get Python slice object selecting sorted times within the given time range. """
    start, end = searchsorted(times, (start_time, end_time), side='left')
    return slice(start, end)


def generate_time_ranges(times, sampling_step=ONE_SEC):
    """ Get time ranges of continuous data segments assuming 1s data sampling. """
    times = round_time_to_seconds(times)
    if times.size == 0:
        return
    dtimes = times[1:] - times[:-1]
    assert dtimes.size == 0 or dtimes.min() >= sampling_step
    idx_start = 0
    for idx_end in (dtimes > sampling_step).nonzero()[0]:
        yield TimeRange(times[idx_start], times[idx_end] + sampling_step)
        idx_start = idx_end + 1
    yield TimeRange(times[idx_start], times[-1] + sampling_step)


def generate_time_range_overlaps(ranges1, ranges2):
    """ Generate overlapping time ranges. """

    def _get_next_range(range_iterator):
        for range_ in range_iterator:
            if not range_.is_empty:
                return range_
        return None

    range1 = _get_next_range(ranges1)
    range2 = _get_next_range(ranges2)

    while range1 and range2:

        if range1.start < range2.start:
            range1 = range1.trim_start(range2.start)
        elif range2.start < range1.start:
            range1 = range1.trim_start(range2.start)
        else: # range1.start == range2.start
            overlap = TimeRange(range1.start, min(range1.end, range2.end))
            yield overlap
            range1 = range1.trim_start(overlap.end)
            range2 = range2.trim_start(overlap.end)

        if range1.is_empty:
            range1 = _get_next_range(ranges1)
        if range2.is_empty:
            range2 = _get_next_range(ranges2)


def round_time_to_seconds(times):
    """Round times to whole seconds."""
    return (times + HALF_SEC).astype('datetime64[s]')
