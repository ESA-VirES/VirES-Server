#-------------------------------------------------------------------------------
#
# Dst index file handling.
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
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

from numpy import loadtxt, array, empty, nan
from .cdf_util import cdf_open
from .time_util import mjd2000_to_datetime
from .aux_common import (
    SingleSourceMixIn, MJD2000TimeMixIn, CdfReader, render_filename,
)

HOURS_TO_DAYS = 1.0 / 24.0
DST_FLAGS = {b"D": 0, b"P": 1} # Definitive / Preliminary(?)


def update_dst(src_file, dst_file):
    """ Update Dst index file. """

    def _ddst(time, dst):
        ddst = empty(dst.shape)
        ddst[:-1] = HOURS_TO_DAYS * abs(
            (dst[1:] - dst[:-1]) / (time[1:] - time[:-1])
        )
        ddst[-1] = nan
        return ddst

    def _write_dst(file_in, dst_file):
        with cdf_open(dst_file, "w") as cdf:
            time, dst, est, ist, flag = parse_dst(file_in)
            cdf["time"], cdf["dst"], cdf["est"], cdf["ist"], cdf["flag"] = (
                time, dst, est, ist, flag
            )
            cdf["ddst"] = _ddst(time, dst)
            start, end = time.min(), time.max()
            cdf.attrs['SOURCE'] = render_filename(
                "SW_OPER_AUX_DST_2__{start}_{end}_0001",
                mjd2000_to_datetime(start), mjd2000_to_datetime(end)
            )
            cdf.attrs['VALIDITY'] = [start, end]

    if isinstance(src_file, str):
        with open(src_file) as file_in:
            _write_dst(file_in, dst_file)
    else:
        _write_dst(src_file, dst_file)


def parse_dst(src_file):
    """ Parse Dst index text file. """
    data = loadtxt(src_file, converters={4: lambda v: float(DST_FLAGS[v])})
    return (
        data[:, 0], data[:, 1], data[:, 2], data[:, 3],
        array(data[:, 4], 'uint8')
    )


class DstReader(SingleSourceMixIn, MJD2000TimeMixIn, CdfReader):
    """ Dst data reader class. """
    TIME_FIELD = "time"
    DATA_FIELDS = ("dst",)
    INTERPOLATION_KIND = "linear"


class DDstReader(SingleSourceMixIn, MJD2000TimeMixIn, CdfReader):
    """ dDst data reader class. """
    TIME_FIELD = "time"
    DATA_FIELDS = ("ddst",)
    INTERPOLATION_KIND = "zero"
