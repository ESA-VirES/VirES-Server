#-------------------------------------------------------------------------------
#
# Orbit direction - extraction from input data
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
# pylint: disable=too-many-arguments, too-few-public-methods

from numpy import array, concatenate
from .util import OutputData
from .common import (
    FLAG_ASCENDING, FLAG_DESCENDING,
    GAP_THRESHOLD, NOMINAL_SAMPLING,
)

FLAGS_ORBIT_DIRECTION = array([FLAG_DESCENDING, FLAG_ASCENDING], 'int8')


def extract_orbit_directions(times, lats):
    """ Extract orbit directions lookup table from the given data. """

    def _process_data(times_all, lats_all):
        for segment in get_continuous_segments(times_all, GAP_THRESHOLD):
            times, lats = times_all[segment], lats_all[segment]
            if times.size < 2:
                continue
            times_extr, type_extr = find_inversion_points(
                *low_pass_filter(times, lats)
            )
            yield OutputData.get_start(
                times[0], FLAGS_ORBIT_DIRECTION[int(lats[1] >= lats[0])]
            )
            yield OutputData.get_body(
                times_extr, FLAGS_ORBIT_DIRECTION[type_extr.astype('int')]
            )
            yield OutputData.get_end(times[-1] + NOMINAL_SAMPLING)

    return OutputData.join(*list(_process_data(times, lats)))


def get_continuous_segments(times, threshold):
    """ Generator producing continuous data slices. The algorithm splits
    the data at gaps exceeding the given threshold.
    """
    dtimes = times[1:] - times[:-1]
    idx_last = 0
    for idx in (dtimes > threshold).nonzero()[0]:
        yield slice(idx_last, idx + 1)
        idx_last = idx + 1
    yield slice(idx_last, None)


def low_pass_filter(times, values):
    """ Non-equidistant 3-element Gaussian smoothing filter.
    The filter preserves the unfiltered edges.
    """
    if values.size < 2:
        return times, values
    tmp = times.astype('float64')
    alpha = (tmp[1:-1] - tmp[:-2]) / (tmp[2:] - tmp[:-2]) # weight factor
    return times, concatenate((
        values[:1],
        0.5 * (values[:-2] * (1 - alpha) + values[1:-1] + values[2:] * alpha),
        values[-1:],
    ))


def find_inversion_points(times, lats):
    """ Find points of maxi./min. latitudes were the orbit direction gets
    inverted.
    """
    index = lookup_extrema(lats)
    tmp, ascending_pass = find_extrema(times.astype('float64'), lats, index)
    extrema_times = tmp.astype(times.dtype)
    return extrema_times, ascending_pass


def lookup_extrema(values):
    """ Find indices of local minimum and maximum of the array values. """
    non_descending = values[1:] - values[:-1] >= 0
    return 1 + (non_descending[1:] != non_descending[:-1]).nonzero()[0]


def find_extrema(x, y, idx):
    """ Find approximate location of the minimum and maximum values. """
    #pylint: disable=invalid-name
    idx0, idx1, idx2 = idx - 1, idx, idx + 1
    x0, y0 = x[idx0], y[idx0]
    a1, a2 = x[idx1] - x0, x[idx2] - x0
    b1, b2 = y[idx1] - y0, y[idx2] - y0
    a1b2, a2b1 = a1*b2, a2*b1
    return (
        x0 + 0.5*(a1*a1b2 - a2*a2b1)/(a1b2 - a2b1),
        ((b2/a2 - b1/a1) / (a2 - a1)) > 0
    )
