#-------------------------------------------------------------------------------
#
# Auxiliary data files handling.
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
from .time_util import datetime_to_mjd2000


KP_FLAGS = {"D": 0, "Q": 1} # Definitive / Quick-look
DST_FLAGS = {"D": 0, "P": 1} # Definitive / Preliminary(?)


def parse_dst(src_file):
    """ Parse Dst index text file. """
    data = loadtxt(src_file, converters={4: lambda v: float(DST_FLAGS[v])})
    return (
        data[:, 0], data[:, 1], data[:, 2], data[:, 3],
        array(data[:, 4], 'uint8')
    )


def parse_kp(src_file):
    """ Parse Kp index text file. """
    data = loadtxt(src_file, converters={3: lambda v: float(KP_FLAGS[v])})
    return (
        data[:, 0], array(data[:, 1], 'uint16'), array(data[:, 2], 'uint16'),
        array(data[:, 3], 'uint8')
    )


def update_dst(src_file, dst_file):
    """ Update Dst index file. """
    with cdf_open(dst_file, "w") as cdf:
        cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
            parse_dst(src_file)
        )


def update_kp(src_file, dst_file):
    """ Update Kp index file. """
    with cdf_open(dst_file, "w") as cdf:
        cdf["time"], cdf["kp"], cdf["ap"], cdf["flag"] = parse_kp(src_file)


def query_dst(filename, start, stop):
    """ Query non-interpolated Dst index values. """
    if not exists(filename):
        return {"time": array([]), "dst": array([])}
    with cdf_open(filename) as cdf:
        return dict(cdf_time_subset(
            cdf, datetime_to_mjd2000(start), datetime_to_mjd2000(stop),
            fields=("time", "dst"), margin=1
        ))


def query_kp(filename, start, stop):
    """ Query non-interpolated Kp index values. """
    if not exists(filename):
        return {"time": array([]), "kp": array([])}
    with cdf_open(filename) as cdf:
        return dict(cdf_time_subset(
            cdf, datetime_to_mjd2000(start), datetime_to_mjd2000(stop),
            fields=("time", "kp"), margin=1
        ))


def query_dst_int(filename, time, nodata=nan):
    """ Query interpolated Dst index values. """
    if exists(filename):
        with cdf_open(filename) as cdf:
            return dict(cdf_time_interp(
                cdf, time, ("dst",), nodata={"dst": nodata}, kind="linear"
            ))
    else:
        return {"dst": full(time.shape, nan)}


def query_kp_int(filename, time, nodata=nan):
    """ Query interpolated Kp index values. """
    if exists(filename):
        with cdf_open(filename) as cdf:
            return dict(cdf_time_interp(
                cdf, time, ("kp",), nodata={"kp": nodata}, kind="nearest"
            ))
    else:
        return {"kp": full(time.shape, nodata)}
