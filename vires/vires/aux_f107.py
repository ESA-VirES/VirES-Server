#-------------------------------------------------------------------------------
#
# AUX_F10_2_ index file handling.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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

from os.path import basename, splitext
from numpy import loadtxt, zeros, isnan
from .cdf_util import cdf_open
from .time_util import mjd2000_to_datetime
from .aux_common import (
    SingleSourceMixIn, MJD2000TimeMixIn, CdfReader, render_filename,
)

# Time tolerance used to check sampling of the F10.7 values
SAMPLING_TOLERANCE = 1e-8 # days, (1e-8d ~ 0.9ms)

# Nominal sampling of the F10.7 data
NOMINAL_SAMPLING = 1.0 # days (one sample per day)

# Parameters of the box-car averaging window
LEFT_WINDOW_SIZE = 40 # days before the central date
RIGHT_WINDOW_SIZE = 40 # days after the central date


class F10_2_Reader(SingleSourceMixIn, MJD2000TimeMixIn, CdfReader):
    """ F10.7 data reader class. """
    TIME_FIELD = "MJD2000"
    DATA_FIELDS = ("F10.7", "F10.7_avg81d", "F10.7_avg81d_count")
    INTERPOLATION_KIND = "linear"


def update_aux_f107_2_(src_file, dst_file):
    """ Update AUX_F10_2_ index file. """

    def _write_aux_f107_2_(file_in, src_file, dst_file):
        time, f107 = parse_aux_f107_2_(file_in)
        _check_time_sampling(time)
        f107_avg, sample_count = _moving_average(f107)

        with cdf_open(dst_file, "w") as cdf:
            (
                cdf["MJD2000"], cdf["F10.7"],
                cdf["F10.7_avg81d"], cdf["F10.7_avg81d_count"],
            ) = time, f107, f107_avg, sample_count
            start, end = time.min(), time.max()
            if src_file:
                cdf.attrs['SOURCE'] = splitext(basename(src_file))[0]
            else:
                cdf.attrs['SOURCE'] = src_file if src_file else render_filename(
                    "SW_OPER_AUX_F10_2__{start}_{end}_0001",
                    mjd2000_to_datetime(start), mjd2000_to_datetime(end)
                )
            cdf.attrs['VALIDITY'] = [start, end]

    if isinstance(src_file, str):
        with open(src_file, encoding="utf8") as file_in:
            _write_aux_f107_2_(file_in, src_file, dst_file)
    else:
        _write_aux_f107_2_(src_file, None, dst_file)


def _moving_average(values, left_window_size=LEFT_WINDOW_SIZE,
                    right_window_size=RIGHT_WINDOW_SIZE):
    """ Moving average (box-car filter) of equidistantly sampled vector of values. """
    assert (values.size,) == values.shape
    counts = zeros(values.size, dtype="int32")
    buffer = zeros(values.size, dtype="float64")
    size = values.size
    for idx in range(-left_window_size, right_window_size + 1):
        source_slice = slice(max(0, +idx), max(0, size + idx))
        target_slice = slice(max(0, -idx), max(0, size - idx))
        mask = ~isnan(values[source_slice])
        counts[target_slice][mask] += 1
        buffer[target_slice][mask] += values[source_slice][mask]
    return buffer / counts, counts


def _check_time_sampling(times, nominal_sampling=NOMINAL_SAMPLING,
                         sampling_tolerance=SAMPLING_TOLERANCE):
    """ Check check time sampling of the dataset. """

    def _is_valid(sampling):
        return abs(sampling - nominal_sampling) < sampling_tolerance

    if len(times) < 2:
        return

    samples = times[1:] - times[:-1]
    min_sample, max_sample = samples.min(), samples.max()
    if not _is_valid(min_sample) or not _is_valid(max_sample):
        raise ValueError(
            "F10.7 data sampling deviates from the expected nominal sampling!"
            f" min_sample: {min_sample}, max_sample: {max_sample},"
            f" nominal_sapling: {nominal_sampling}"
        )


def parse_aux_f107_2_(src_file):
    """ Parse AUX_F10_2_ index file. """
    data = loadtxt(src_file)
    return (data[:, 0], data[:, 1])
