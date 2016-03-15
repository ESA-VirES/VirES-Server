#-------------------------------------------------------------------------------
# $Id$
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
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

try:
    # available in Python 2.7+
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict
import math

from django.conf import settings
from spacepy import pycdf
import numpy as np
from scipy.interpolate import interp1d
from eoxserver.core.util.timetools import isoformat

from vires import jdutil
from vires.util import get_total_seconds


def _open_db(filename, mode="r"):
    try:
        cdf = pycdf.CDF(filename, "")
    except pycdf.CDFError:
        cdf = pycdf.CDF(filename)
        if mode == "w":
            cdf.readonly(False)
    return cdf


def mjd2000_to_datetime(mjd):
    return jdutil.jd_to_datetime(mjd + 2451544.5)


def datetime_to_mjd2000(dt):
    return jdutil.datetime_to_jd(dt) - 2451544.5


def update_db(file_dst, file_kp):
    cdf_dst = _open_db(settings.VIRES_AUX_DB_DST, "w")
    dst = _parse_dst(file_dst)
    cdf_dst["time"] = dst[0]
    cdf_dst["dst"] = dst[1]
    cdf_dst["est"] = dst[2]
    cdf_dst["ist"] = dst[3]
    cdf_dst.close()

    cdf_kp = _open_db(settings.VIRES_AUX_DB_KP, "w")
    kp = _parse_kp(file_kp)
    cdf_kp["time"] = kp[0]
    cdf_kp["kp"] = kp[1]
    cdf_kp["ap"] = kp[2]
    cdf_kp.close()


def _parse_dst(filename):
    def _parse_line(line):
        mjd, dst, est, ist, flag = line.strip().split()
        return float(mjd), float(dst), float(est), float(ist)

    with open(filename) as f:
        arr = np.array([
            _parse_line(line) for line in f
            if "#" not in line
        ])

    return arr.T


def _parse_kp(filename):
    def _parse_line(line):
        mjd, kp, ap, flag = line.strip().split()
        return float(mjd), int(kp), int(ap)

    with open(filename) as f:
        arr = np.array([
            _parse_line(line) for line in f
            if "#" not in line
        ])

    return arr.T


def _read_cdf(filename, start, stop, fields):
    cdf = _open_db(filename)

    #second, third = cdf["time"][1:3]
    #resolution = third - second

    begin = cdf["time"][0]  # second - resolution
    end = cdf["time"][-1]
    resolution = (end - begin) / len(cdf["time"])

    # TODO: Think how getting out of bound should be handled
    if start > stop:
        tmp = stop
        stop = start
        start = tmp
    if start > end or stop < start:
        raise ValueError("Request outside of defined aux bounds: [%s, %s]"
            % (
                isoformat(mjd2000_to_datetime(begin)),
                isoformat(mjd2000_to_datetime(end))
            )
        )
    if start < begin:
        start = begin
    if stop > end:
        stop = end

    # if start < begin or stop > end:
    #     raise ValueError("Request outside of defined aux bounds: [%s, %s]"
    #         % (
    #             isoformat(mjd2000_to_datetime(begin)),
    #             isoformat(mjd2000_to_datetime(end))
    #         )
    #     )

    low = int(math.floor((start - begin) / resolution))
    high = int(math.ceil((stop - begin) / resolution))

    return dict([(field, cdf[field][low-1:high+1]) for field in fields])


def _query_dst(input_arr, start, stop):
    values = _read_cdf(
        settings.VIRES_AUX_DB_DST, start, stop,
        ("time", "dst", "est", "ist")
    )

    return {
        "dst": interp1d(values["time"], values["dst"])(input_arr)
    }


def _query_kp(input_arr, start, stop):
    values = _read_cdf(
        settings.VIRES_AUX_DB_KP, start, stop,
        ("time", "kp")
    )

    return {
        "kp": interp1d(values["time"], values["kp"], kind="nearest")(input_arr)
    }


def query_db(start, stop, count, dst_nodata_value=None, kp_nodata_value=None):
    start = datetime_to_mjd2000(start)
    stop = datetime_to_mjd2000(stop)

    input_arr = np.linspace(start, stop, count)

    values = {}
    try:
        values.update(_query_dst(input_arr, start, stop))
    except:
        if dst_nodata_value is None:
            raise
        values["dst"] = np.empty(count)
        values["dst"].fill(dst_nodata_value)
    try:
        values.update(_query_kp(input_arr, start, stop))
    except:
        if kp_nodata_value is None:
            raise
        values["kp"] = np.empty(count)
        values["kp"].fill(kp_nodata_value)

    return values


# Query Not Interpolated Dst values
def query_dst_ni(start, stop):
    start = datetime_to_mjd2000(start)
    stop = datetime_to_mjd2000(stop)
    values = _read_cdf(
        settings.VIRES_AUX_DB_DST, start, stop,
        ("time", "dst")
    )
    values["time"] = map(float, values["time"])

    return values


# Query Not Interpolated kp values
def query_kp_ni(start, stop):
    start = datetime_to_mjd2000(start)
    stop = datetime_to_mjd2000(stop)
    values = _read_cdf(
        settings.VIRES_AUX_DB_KP, start, stop,
        ("time", "kp")
    )

    values["time"] = map(float, values["time"])

    return values
