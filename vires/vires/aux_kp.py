#-------------------------------------------------------------------------------
#
# Kp index file handling.
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

# Note: the source Kp are not true Kp but rather Kp10.

from numpy import loadtxt, array
from .cdf_util import cdf_open
from .time_util import mjd2000_to_datetime
from .aux_common import (
    SingleSourceMixIn, MJD2000TimeMixIn, BaseReader, render_filename,
)

KP_FLAGS = {"D": 0, "Q": 1} # Definitive / Quick-look


class KpReader(SingleSourceMixIn, MJD2000TimeMixIn, BaseReader):
    """ Kp data reader class. """
    TIME_FIELD = "time"
    DATA_FIELDS = ("kp",)
    INTERPOLATION_KIND = "nearest"


def update_kp(src_file, dst_file):
    """ Update Kp index file. """

    def _write_kp(file_in, dst_file):
        with cdf_open(dst_file, "w") as cdf:
            time, kp_, ap_, flag = parse_kp(file_in)
            cdf["time"], cdf["kp"], cdf["ap"], cdf["flag"] = time, kp_, ap_, flag
            start, end = time.min(), time.max()
            cdf.attrs['SOURCE'] = render_filename(
                "SW_OPER_AUX_KP__2__{start}_{end}_0001",
                mjd2000_to_datetime(start), mjd2000_to_datetime(end)
            )
            cdf.attrs['VALIDITY'] = [start, end]

    if isinstance(src_file, basestring):
        with open(src_file, "rb") as file_in:
            _write_kp(file_in, dst_file)
    else:
        _write_kp(src_file, dst_file)


def parse_kp(src_file):
    """ Parse Kp index text file. """
    data = loadtxt(src_file, converters={3: lambda v: float(KP_FLAGS[v])})
    return (
        data[:, 0], array(data[:, 1], 'uint16'), array(data[:, 2], 'uint16'),
        array(data[:, 3], 'uint8')
    )
