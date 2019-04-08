#-------------------------------------------------------------------------------
#
# AUX_F10_2_ index file handling.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from os.path import exists, basename, splitext
from numpy import loadtxt, array, nan

from .util import full
from .cdf_util import cdf_open, cdf_time_subset, cdf_time_interp
from .time_util import datetime_to_mjd2000

FIELD_TIME = "MJD2000"
FIELD_F107 = "F10.7"


def parse_aux_f107_2_(src_file):
    """ Parse AUX_F10_2_ index file. """
    data = loadtxt(src_file)
    return (data[:, 0], data[:, 1])


def update_aux_f107_2_(src_file, dst_file):
    """ Update AUX_F10_2_ index file. """
    with open(src_file, "rb"):
        with cdf_open(dst_file, "w") as cdf:
            cdf[FIELD_TIME], cdf[FIELD_F107] = parse_aux_f107_2_(src_file)
            cdf.attrs['SOURCE'] = splitext(basename(src_file))[0]


def query_aux_f107_2_(filename, start, stop, fields=(FIELD_TIME, FIELD_F107)):
    """ Query non-interpolated F10.7 index values. """
    if not exists(filename):
        return {field: array([]) for field in fields}

    with cdf_open(filename) as cdf:
        return dict(cdf_time_subset(
            cdf, datetime_to_mjd2000(start), datetime_to_mjd2000(stop),
            fields=fields, margin=1, time_field=FIELD_TIME,
        ))


def query_aux_f107_2__int(filename, time, nodata=None, fields=(FIELD_F107,)):
    """ Query interpolated F10.7 index values. """
    if exists(filename):
        with cdf_open(filename) as cdf:
            return dict(cdf_time_interp(
                cdf, time, fields, nodata=nodata, kind="linear",
                time_field=FIELD_TIME,
            ))
    else:
        nodata = nodata or {}
        return {
            field: full(time.shape, nodata.get(field, nan))
            for field in fields
        }
