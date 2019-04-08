#-------------------------------------------------------------------------------
#
# Dst index file handling.
#
# Project: VirES
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
from numpy import loadtxt, array, nan

from .util import full
from .cdf_util import cdf_open, cdf_time_subset, cdf_time_interp
from .time_util import datetime_to_mjd2000, mjd2000_to_datetime, timedelta

DST_FLAGS = {"D": 0, "P": 1} # Definitive / Preliminary(?)


def parse_dst(src_file):
    """ Parse Dst index text file. """
    data = loadtxt(src_file, converters={4: lambda v: float(DST_FLAGS[v])})
    return (
        data[:, 0], data[:, 1], data[:, 2], data[:, 3],
        array(data[:, 4], 'uint8')
    )


def generate_dst_filename(times):
    """ Generate normal AUX_DST_2_ Swarm product filename. """
    def _format_time(mjd2000):
        dt_ = mjd2000_to_datetime(mjd2000) + timedelta(microseconds=500000)
        return dt_.strftime("%Y%m%dT%H%M%S")

    return "SW_OPER_AUX_DST_2__%s_%s_0001" % (
        _format_time(times.min()), _format_time(times.max()),
    )


def update_dst(src_file, dst_file):
    """ Update Dst index file. """
    with open(src_file, "rb"):
        with cdf_open(dst_file, "w") as cdf:
            time, dst, est, ist, flag = parse_dst(src_file)
            cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
                time, dst, est, ist, flag
            )
            cdf.attrs['SOURCE'] = generate_dst_filename(time)


def query_dst(filename, start, stop, fields=("time", "dst")):
    """ Query non-interpolated Dst index values. """
    if not exists(filename):
        return {field: array([]) for field in fields}

    with cdf_open(filename) as cdf:
        return dict(cdf_time_subset(
            cdf, datetime_to_mjd2000(start), datetime_to_mjd2000(stop),
            fields=fields, margin=1
        ))


def query_dst_int(filename, time, nodata=None, fields=("dst",)):
    """ Query interpolated Dst index values. """
    if exists(filename):
        with cdf_open(filename) as cdf:
            return dict(cdf_time_interp(
                cdf, time, fields, nodata=nodata, kind="linear"
            ))
    else:
        nodata = nodata or {}
        return {
            field: full(time.shape, nodata.get(field, nan))
            for field in fields
        }
