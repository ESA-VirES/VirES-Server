#-------------------------------------------------------------------------------
#
# Orbit number file handling.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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
from django.utils.dateparse import parse_datetime
from numpy import loadtxt, array, nan
from .cdf_util import cdf_open, cdf_time_subset, cdf_time_interp


def parse_orbit_counter_file(src_file):
    """ Parse Swarm orbit counter text file. """
    data = loadtxt(
        src_file,
        skiprows=1,
        converters={2: (lambda v: 0), 3: (lambda v: 0)}
    )
    return (
        data[:, 0].astype('uint32'), data[:, 1], data[:, 4],
        data[:, 5].astype('uint8')
    )


def update_orbit_counter_file(src_file, dst_file):
    """ Update Swarm orbit counter text file. """
    with cdf_open(dst_file, "w") as cdf:
        cdf["orbit"], cdf["MJD2000"], cdf["phi_AN"], cdf["Source"] = (
            parse_orbit_counter_file(src_file)
        )
