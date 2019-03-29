#-------------------------------------------------------------------------------
#
#  Gap-aware 1D interpolation.
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

from logging import getLogger
from numpy import (
    array, arange, empty, isnan, invert, diff, inf, nan, concatenate,
    searchsorted,
)
import scipy
from scipy.interpolate import interp1d
from vires.util import full


class Interp1D(object):
    """ 1D interpolator.
    This class is optimised for repeated 1D interpolation of multiple
    dataset using the same target sampling (x_dst).
    NOTE: x_src and x_dst must be sorted in ascending order.
    """

    def __init__(self, x_src, x_dst, gap_threshold=inf,
                 segment_neighbourhood=0, logger=None):
        """ Initialize interpolator. """
        self.x_src = x_src
        self.x_dst = x_dst
        self.gap_threshold = gap_threshold
        self.segment_neighbourhood = (
            max(0, min(gap_threshold, segment_neighbourhood))
        )
        self.prm = {
            "bounds_error": False,
            "copy": False,
        }
        if scipy.__version__ >= '0.14':
            self.prm['assume_sorted'] = True
        self._indices_nearest = None
        self._data_zero = None
        self.logger = logger or getLogger(__name__)
        self._supported_kinds = {
            "nearest": self._nearest,
            "zero": self._zero,
        }

    def __call__(self, y_src, kind):
        """ Interpolate values. """

        if len(self.x_src) != len(y_src):
            raise ValueError(
                "x_src and y_src arrays must be equal in length along "
                "interpolation axis."
            )

        try:
            handler = self._supported_kinds[kind]
        except KeyError:
            raise ValueError("Invalid interpolation kind %r!" % kind)

        return handler(y_src)

    @property
    def indices_nearest(self):
        """ Get indices of the nearest neighbour  interpolation. """
        if not self._indices_nearest:
            self._init_nearest()
        return self._indices_nearest

    @property
    def data_zero(self):
        """ Get indices of the zero-order interpolation. """
        if not self._data_zero:
            self._init_zero()
        return self._data_zero

    def _nearest(self, y_src):
        """ Nearest neighbour interpolation. """
        return self._select_values(y_src, *self.indices_nearest)

    def _zero(self, y_src):
        """ Zero-kind interpolation. """
        return self._select_values(y_src, *self.data_zero)

    def _select_values(self, y_src, idx_nan, idx_valid, idx_source):
        """ Select the interpolated values. """
        y_dst = empty((len(self.x_dst),) + y_src.shape[1:])
        if y_dst.size > 0:
            y_dst[idx_nan] = nan
            # NOTE: workaround for the empty multi-dimensional slicing bug
            #       in NumPy v1.7.1
            if idx_valid.size > 0:
                y_dst[idx_valid] = y_src[idx_source]
        return y_dst

    def _init_nearest(self):
        """ Initialize the nearest neighbour interpolation. """
        self._indices_nearest = self._get_value_indices(
            "nearest", self.segment_neighbourhood, self.segment_neighbourhood
        )

    def _init_zero(self):
        """ Initialize the zero-kind interpolation. """
        self._data_zero = self._get_value_indices(
            "zero", 0, self.segment_neighbourhood
        )

    def _get_value_indices(self, kind, lower_neighbourhood, upper_neighbourhood):
        self.logger.debug("%s: x_src shape: %s", kind, self.x_src.shape)
        self.logger.debug("%s: x_dst shape: %s", kind, self.x_dst.shape)
        self.logger.debug("%s: gap_threshold: %s", kind, self.gap_threshold)
        self.logger.debug(
            "%s: lower_neighbourhood: %s", kind, lower_neighbourhood
        )
        self.logger.debug(
            "%s: upper_neighbourhood: %s", kind, upper_neighbourhood
        )

        index = full(self.x_dst.shape, nan)
        # iterate over the contiguous value ranges
        ranges = self._contiguous_ranges(self.x_src, self.gap_threshold)
        for low, high in ranges:
            self.logger.debug("%s: contiguous range: %d:%d", kind, low, high)
            x_l = self.x_src[low] - max(0.0, lower_neighbourhood)
            x_h = self.x_src[high-1] + max(0.0, upper_neighbourhood)
            if high - low == 1:
                # single value segment
                x_src = array([x_l, x_h])
                i_src = array([low, low])
            else:
                # regular multi-value segment
                x_src = self.x_src[low:high]
                i_src = arange(low, high)
                x_src = concatenate(([x_l], x_src, [x_h]))
                i_src = concatenate(([low], i_src, [high-1]))
            # get range of the data overlapping the interpolated segment
            idx_dst_low = searchsorted(self.x_dst, x_l, side='left')
            idx_dst_high = searchsorted(self.x_dst, x_h, side='right')
            # segment interpolation
            if idx_dst_high > idx_dst_low:
                index[idx_dst_low:idx_dst_high] = interp1d(
                    x_src, i_src, kind=kind, **self.prm
                )(self.x_dst[idx_dst_low:idx_dst_high])
        # extract index mapping
        is_nan = isnan(index)
        idx_nan = is_nan.nonzero()[0]
        idx_valid = invert(is_nan).nonzero()[0]
        idx_source = index[idx_valid].astype('int')

        self.logger.debug(
            "%s: %d mapped, %d invalids", kind, len(idx_valid), len(idx_nan)
        )

        return idx_nan, idx_valid, idx_source

    @staticmethod
    def _contiguous_ranges(x_src, gap_threshold):
        """ Generator returning contiguous ranges of the interpolated
        variable.
        """
        idx_low = 0
        for idx_high in (diff(x_src) > gap_threshold).nonzero()[0] + 1:
            yield idx_low, idx_high
            idx_low = idx_high
        idx_high = len(x_src)
        if idx_high > 0:
            yield idx_low, idx_high
