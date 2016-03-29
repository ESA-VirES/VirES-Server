#-------------------------------------------------------------------------------
#
# Time utilities.
#
# Project: VirES-Server
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

from .contrib.jdutil import (
    hmsm_to_days, jd_to_date, days_to_hmsm, mjd_to_jd, datetime,
    timedelta_to_days, date_to_jd, jd_to_mjd, datetime_to_jd, jd_to_datetime,
)

JD_2000 = 2451544.5

def mjd2000_to_datetime(mjd):
    """ Convert Modified Julian Date 2000 to `datetime.datetime` object. """
    return jd_to_datetime(mjd + JD_2000)

def datetime_to_mjd2000(dt_obj):
    """ Convert `datetime.datetime` object to Modified Julian Date 2000. """
    return datetime_to_jd(dt_obj) - JD_2000
