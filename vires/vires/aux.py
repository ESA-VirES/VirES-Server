#-------------------------------------------------------------------------------
#
# Auxiliary data files handling.
#
# Project: VirES
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

import math
from contextlib import closing
import numpy as np
from scipy.interpolate import interp1d
from django.conf import settings
from eoxserver.core.util.timetools import isoformat

from .cdf_util import cdf_open
from .time_util import mjd2000_to_datetime, datetime_to_mjd2000
from .util import get_total_seconds

KP_FLAGS = {"D": 0, "Q": 1}
DST_FLAGS = {"D": 0, "P": 1}


def parse_dst(src_file):
    """ Parse Dst index text file. """
    data = np.loadtxt(src_file, converters={4: lambda v: float(DST_FLAGS[v])})
    return (
        data[:, 0], data[:, 1], data[:, 2], data[:, 3],
        np.array(data[:, 4], 'uint8')
    )


def update_dst(src_file, dst_file=None):
    """ Update Dst index file. """
    if dst_file is None:
        dst_file = settings.VIRES_AUX_DB_DST

    with closing(cdf_open(dst_file, "w")) as cdf:
        cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
            parse_dst(src_file)
        )


def parse_kp(src_file):
    """ Parse Kp index text file. """
    data = np.loadtxt(src_file, converters={3: lambda v: float(KP_FLAGS[v])})
    return (
        data[:, 0], data[:, 1], data[:, 2], np.array(data[:, 3], 'uint8')
    )


def update_kp(src_file, dst_file=None):
    """ Update Kp index file. """
    if dst_file is None:
        dst_file = settings.VIRES_AUX_DB_KP

    with closing(cdf_open(dst_file, "w")) as cdf:
        cdf["time"], cdf["kp"], cdf["ap"], cdf["flag"] = parse_kp(src_file)


def _read_cdf(filename, start, stop, fields):
    # TODO: The file is not guaranteed to exist. Implement a proper check.
    # NOTE: Where is the file closed?!
    cdf = cdf_open(filename)

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
        raise ValueError(
            "Request outside of defined aux bounds: [%s, %s]" % (
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
