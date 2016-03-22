#-------------------------------------------------------------------------------
#
# CDF file-format utilities
#
# Project: VirES-Server
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
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

from os.path import exists
from math import ceil, floor
from numpy import empty, nan, max as amax, min as amin
import scipy
from scipy.interpolate import interp1d
from spacepy import pycdf

try:
    from numpy import full
except ImportError:
    def full(shape, value, dtype=None, order='C'):
        """ Numpy < 1.8 workaround. """
        arr = empty(shape, dtype, order)
        arr.fill(value)
        return arr


def cdf_open(filename, mode="r"):
    """ Open a new or an existing  CDF file.
    Allowed modes are 'r' (read-only) and 'w' (read-write).
    A new CDF file is created in for the 'w' mode if it does not exist.
    The returned object can be used with the `with` command.
    """
    if mode == "r":
        cdf = pycdf.CDF(filename)
    elif mode == "w":
        if exists(filename):
            cdf = pycdf.CDF(filename)
            cdf.readonly(False)
        else:
            cdf = pycdf.CDF(filename, "")
    else:
        raise ValueError("Invalid mode value %r!" % mode)
    return cdf


def cdf_time_subset(cdf, start, stop, fields, margin=0):
    """ Extract subset of the listed `fields` from a CDF data file.
    The extracted range of values match times which lie within the given
    closed time interval. The time interval is defined by the MDJ2000 `start`
    and `stop` values.
    The `margin` parameter is used to extend the index range by N surrounding
    elements. Negative margin is allowed.
    """
    time = cdf['time']
    idx_start, idx_stop = 0, time.shape[0]

    if start > stop:
        start, stop = stop, start

    if time.shape[0] > 0:
        start = max(start, time[0])
        stop = min(stop, time[-1])
        time_span = time[-1] - time[0]
        if time_span > 0:
            resolution = (time.shape[0] - 1) / time_span
            idx_start = int(ceil((start - time[0]) * resolution))
            idx_stop = max(0, 1 + int(floor((stop - time[0]) * resolution)))
        elif start > time[-1] or stop < time[0]:
            idx_start = idx_stop # empty selection

    if margin != 0:
        if idx_start < time.shape[0]:
            idx_start = max(0, idx_start - margin)
        if idx_stop > 0:
            idx_stop = max(0, idx_stop + margin)

    return [(field, cdf[field][idx_start:idx_stop]) for field in fields]


def cdf_time_interp(cdf, time, fields, min_len=2, **interp1d_prm):
    """ Read values of the listed fields from the CDF file and interpolate
    them at the given time values (the `time` array of MDJ2000 values).
    The data exceeding the time interval of the source data is filled with the
    `fill_value`. The function accepts additional keyword arguments which are
    passed to the `scipy.interpolate.interp1d` interpolation (such as `kind`
    and `fill_value`).
    """
    # additional interpolation parameters
    if scipy.__version__ >= '0.14':
        interp1d_prm['assume_sorted'] = True
    interp1d_prm['copy'] = False
    interp1d_prm['bounds_error'] = False

    # check minimal length required by the chosen kind of interpolation
    if time.size > 0 and cdf['time'].shape[0] > min_len:
        return [
            (field, interp1d(cdf["time"], cdf[field], **interp1d_prm)(time))
            for field in fields
        ]
    else:
        return [
            (field, full(time.shape, interp1d_prm.get("fill_value", nan)))
            for field in fields
        ]
