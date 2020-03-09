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
from numpy import loadtxt
from .cdf_util import cdf_open
from .time_util import mjd2000_to_datetime
from .aux_common import (
    SingleSourceMixIn, MJD2000TimeMixIn, BaseReader, render_filename,
)


class F10_2_Reader(SingleSourceMixIn, MJD2000TimeMixIn, BaseReader):
    """ F10.7 data reader class. """
    TIME_FIELD = "MJD2000"
    DATA_FIELDS = ("F10.7",)
    INTERPOLATION_KIND = "linear"


def update_aux_f107_2_(src_file, dst_file):
    """ Update AUX_F10_2_ index file. """

    def _write_aux_f107_2_(file_in, src_file, dst_file):
        with cdf_open(dst_file, "w") as cdf:
            time, f107 = parse_aux_f107_2_(file_in)
            cdf["MJD2000"], cdf["F10.7"] = time, f107
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
        with open(src_file) as file_in:
            _write_aux_f107_2_(file_in, src_file, dst_file)
    else:
        _write_aux_f107_2_(src_file, None, dst_file)


def parse_aux_f107_2_(src_file):
    """ Parse AUX_F10_2_ index file. """
    data = loadtxt(src_file)
    return (data[:, 0], data[:, 1])
