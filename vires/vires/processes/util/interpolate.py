#-------------------------------------------------------------------------------
#
#  1D interpolation
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from numpy import arange, empty, isnan, invert
import scipy
from scipy.interpolate import interp1d

NAN = float("NaN")

class Interp1D(object):
    """ 1D interpolator. """

    def __init__(self, x_src, x_dst, assume_sorted=True):
        """ Initialize interpolator. """

        if len(x_src) < 2:
            raise ValueError("x_src must have at least 2 entries!")

        self.x_src = x_src
        self.x_dst = x_dst
        self.prm = {
            "bounds_error": False,
            "copy": False,
        }
        if scipy.__version__ >= '0.14':
            self.prm['assume_sorted'] = assume_sorted
        self._data_nearest = None

    def __call__(self, y_src, kind):
        """ Interpolate values. """

        if len(self.x_src) != len(y_src):
            raise ValueError(
                "x_src and y_src arrays must be equal in length along "
                "interpolation axis."
            )

        if kind == "nearest":
            return self._nearest(y_src)
        else:
            raise ValueError("Invalid interpolation kind %r!" % kind)

    def _init_nearest(self):
        """ Initialize the nearest neighbour interpolation. """
        idx = interp1d(
            self.x_src, arange(len(self.x_src)), kind="nearest", **self.prm
        )(self.x_dst)
        is_nan = isnan(idx)
        idx_nan = is_nan.nonzero()[0]
        idx_valid = invert(is_nan).nonzero()[0]
        idx_nearest = idx[idx_valid].astype('int')
        # save mapping
        self._data_nearest = (idx_nan, idx_valid, idx_nearest)

    def _nearest(self, y_src):
        """ Nearest neighbour interpolation. """
        if not self._data_nearest:
            self._init_nearest()
        idx_nan, idx_valid, idx_nearest = self._data_nearest
        y_dst = empty((len(self.x_dst),) + y_src.shape[1:])
        if y_dst.size > 0:
            y_dst[idx_nan] = NAN
            y_dst[idx_valid] = y_src[idx_nearest]
        return y_dst
