#-------------------------------------------------------------------------------
#
#  Scalar F107 value retrieval.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=too-many-locals,too-many-arguments

from vires.cache_util import cache_path
from vires.data.vires_settings import CACHED_PRODUCT_FILE
from .time_series import IndexF107

F107_AVG81D_VARIABLE = "F107_avg81d"
F107_DAILY_VARIABLE = "F107"
F107_PRODUCT_TYPE = "AUX_F10_2_"


def get_f107_avg81s_value(mjd2000):
    """ Get F10.7 81-days average index value for the given MJD2000 time. """
    return {
        "f107": _get_f107_value(mjd2000, F107_AVG81D_VARIABLE, F107_PRODUCT_TYPE),
    }


def get_f107_daily_value(mjd2000):
    """ Get F10.7 daily index value for the given MJD2000 time. """
    return {
        "f107": _get_f107_value(mjd2000, F107_DAILY_VARIABLE, F107_PRODUCT_TYPE),
    }


def _get_f107_value(mjd2000, variable, product_type):
    """ Get F10.7 index value for the given MJD2000 time. """
    index_f10 = IndexF107(cache_path(CACHED_PRODUCT_FILE[product_type]))
    return index_f10.interpolate(
        mjd2000, variables=[variable], cdf_type=None
    )[variable][0]
