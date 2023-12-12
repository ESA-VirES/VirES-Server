#-------------------------------------------------------------------------------
#
# Handling of the GFZ orbit counter file format used for GOCE, GRACE, and
# GRACE-FO missions.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
from tempfile import NamedTemporaryFile
from shutil import copyfileobj
from numpy import zeros
from ..cdf_util import cdf_open, cdf_rawtime_to_mjd2000


def update_gfz_orbit_counter_file(src_file, dst_file):
    """ Update GRACE and GRACE-FO orbit counter file. """
    if isinstance(src_file, str):
        _update_gfz_orbit_counter_file(src_file, dst_file)
    else:
        with NamedTemporaryFile() as ftemp:
            copyfileobj(src_file, ftemp, 1024*1024)
            ftemp.flush()
            _update_gfz_orbit_counter_file(ftemp.name, dst_file)


def _update_gfz_orbit_counter_file(src_file, dst_file):

    with cdf_open(src_file) as cdf_src:
        with cdf_open(dst_file, "w") as cdf_dst:
            timestamp = cdf_rawtime_to_mjd2000(
                cdf_src.raw_var('Timestamp')[...],
                cdf_src['Timestamp'].type()
            )
            cdf_dst.attrs.update({
                "SOURCE": (
                    str(cdf_src.attrs["TITLE"][0])
                    if "TITLE" in cdf_src.attrs else
                    splitext(basename(src_file))[0]
                ),
                "VALIDITY": [timestamp.min(), timestamp.max()],
            })
            cdf_dst["MJD2000"] = timestamp
            cdf_dst["orbit"] = cdf_src['OrbitNo'][...].astype('uint32')
            cdf_dst["phi_AN"] = cdf_src['Longitude'][...]
            cdf_dst["Source"] = zeros(timestamp.shape, dtype='uint8')
