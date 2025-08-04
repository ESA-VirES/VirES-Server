#-------------------------------------------------------------------------------
#
#  Gap-aware 1D interpolation.
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
## pylint: disable=too-few-public-methods,too-many-arguments,too-many-locals

from logging import getLogger
from numpy import (
    arange, empty, isnan, invert, diff, inf, nan, concatenate,
    searchsorted, full, floor, clip, stack, expand_dims,
)
import scipy
from scipy.interpolate import interp1d


class Interp1D():
    """ 1D interpolator.
    This class is optimised for repeated 1D interpolation of multiple
    datasets using the same target sampling (x_dst).
    NOTE: both x_src and x_dst must be sorted in ascending order.
    """
    DEFAULT_KIND = "nearest"

    def __init__(self, x_src, x_dst, gap_threshold=inf,
                 segment_neighbourhood=0, logger=None):
        self.logger = logger or getLogger(__name__)
        self.x_src = x_src
        self.x_dst = x_dst
        self.gap_threshold = max(0, gap_threshold)
        self.segment_neighbourhood = (
            max(0, min(gap_threshold, segment_neighbourhood))
        )
        self._interpolators = {}
        self._iterpolator_classes = {
            "nearest": NearestNeighbour1DInterpolator,
            "zero": PreviousNeighbour1DInterpolator,
            "previous": PreviousNeighbour1DInterpolator,
            "linear": Linear1DInterpolator,
            "cubic": Cubic1DInterpolator,
        }

    def __call__(self, y_src, dy_src=None, kind=DEFAULT_KIND):
        """ Interpolate values. """

        if len(self.x_src) != len(y_src):
            raise ValueError(
                "x_src and y_src arrays must be equal in length along "
                "interpolation axis. "
                "dy_src is an optional array of tangent (rate of change) "
                "values, required by the cubic Hermite spline interpolation, "
                "and it must be of the same size as y_src or None."
            )

        if kind == "cubic" and dy_src is None:
            # fallback to linear interpolation if the tangents are not provided
            kind = "linear"

        iterpolator = self._interpolators.get(kind)

        if not iterpolator:
            try:
                iterpolator_class = self._iterpolator_classes[kind]
            except KeyError:
                raise ValueError("Invalid interpolation kind {kind!r}") from None

            self._interpolators[kind] = iterpolator = iterpolator_class(
                self.x_src, self.x_dst,
                self.gap_threshold,
                self.segment_neighbourhood,
            )

        return iterpolator(y_src, dy_src)


class BaseNeighbour1DInterpolator():
    """ Base neighbour 1D interpolator. """

    def __init__(self, x_src, x_dst, gap_threshold,
                 lower_neighbourhood, upper_neighbourhood):
        self.x_dst_shape = x_dst.shape
        self.idx_nan, self.idx_valid, self.index = self._get_indices(
            x_src, x_dst,
            gap_threshold=max(0, gap_threshold),
            lower_neighbourhood=max(0, lower_neighbourhood),
            upper_neighbourhood=max(0, upper_neighbourhood),
        )

    def __call__(self, y_src, dy_src=None):
        y_dst = empty(self.x_dst_shape[:1] + y_src.shape[1:])
        if y_dst.size > 0:
            y_dst[self.idx_nan] = nan
            y_dst[self.idx_valid] = y_src[self.index]
        return y_dst

    @staticmethod
    def _find_indices(x_in, i_in, x_out):
        raise NotImplementedError

    def _get_indices(self, x_src, x_dst, gap_threshold,
                     lower_neighbourhood, upper_neighbourhood):
        """ Get valid/invalid values mask and mapping of the source
        to the destination values.
        """
        segments = _generate_contigous_segments(
            x_src, x_dst, gap_threshold,
            lower_neighbourhood, upper_neighbourhood,
        )

        index = full(x_dst.shape, nan)
        for segment in segments:
            (
                (x_l, x_h),
                (idx_src_low, idx_src_high),
                (idx_dst_low, idx_dst_high),
            ) = segment

            index[idx_dst_low:idx_dst_high] = self._find_indices(
                concatenate(
                    ([x_l], x_src[idx_src_low:idx_src_high], [x_h])
                ),
                concatenate(
                    ([idx_src_low], arange(idx_src_low, idx_src_high), [idx_src_high-1])
                ),
                x_dst[idx_dst_low:idx_dst_high]
            )

        idx_nan, idx_valid = _get_nan_mask(index)
        index_source = index[idx_valid].astype("int")

        return idx_nan, idx_valid, index_source


class NearestNeighbour1DInterpolator(BaseNeighbour1DInterpolator):
    """ Nearest neighbour 1D interpolator. """

    def __init__(self, x_src, x_dst, gap_threshold=inf, segment_neighbourhood=0):
        super().__init__(
            x_src=x_src,
            x_dst=x_dst,
            gap_threshold=gap_threshold,
            lower_neighbourhood=segment_neighbourhood,
            upper_neighbourhood=segment_neighbourhood,
        )

    @staticmethod
    def _find_indices(x_in, i_in, x_out):
        options = {
            "kind": "nearest",
            "bounds_error": False,
            "copy": False,
        }
        if scipy.__version__ >= "0.14":
            options["assume_sorted"] = True
        return interp1d(x_in, i_in, **options)(x_out)


class PreviousNeighbour1DInterpolator(BaseNeighbour1DInterpolator):
    """ Previous neighbour 1D interpolator. """

    def __init__(self, x_src, x_dst, gap_threshold=inf, segment_neighbourhood=0):
        super().__init__(
            x_src=x_src,
            x_dst=x_dst,
            gap_threshold=gap_threshold,
            lower_neighbourhood=0,
            upper_neighbourhood=segment_neighbourhood,
        )

    @staticmethod
    def _find_indices(x_in, i_in, x_out):
        options = {
            "kind": "previous",
            "bounds_error": False,
            "copy": False,
        }
        if scipy.__version__ >= "0.14":
            options["assume_sorted"] = True
        return interp1d(x_in, i_in, **options)(x_out)


class BaseSpline1DInterpolator():
    """ Base piecewise 1D interpolator. """

    @classmethod
    def _get_indices(cls, x_src, x_dst, gap_threshold,
                     lower_neighbourhood, upper_neighbourhood):
        """ Get valid/invalid values mask and mapping of the source
        to the destination values.
        """
        index = full(x_dst.shape, -1)
        base = full(x_dst.shape, nan)

        segments = _generate_contigous_segments(
            x_src, x_dst, gap_threshold,
            lower_neighbourhood, upper_neighbourhood,
        )

        for segment in segments:
            (
                _,
                (idx_src_low, idx_src_high),
                (idx_dst_low, idx_dst_high),
            ) = segment

            # skip single element segments
            if idx_src_high - idx_src_low < 2:
                continue

            (
                index[idx_dst_low:idx_dst_high],
                base[idx_dst_low:idx_dst_high]
            ) = cls._get_segment_index_and_parameter(
                arange(idx_src_low, idx_src_high),
                x_src[idx_src_low:idx_src_high],
                x_dst[idx_dst_low:idx_dst_high]
            )

        idx_nan, idx_valid = _get_nan_mask(base)

        index = index[idx_valid]
        base = base[idx_valid]

        index = stack((index, index+1), axis=1)
        base = stack((1.0 - base, base), axis=1)

        return idx_nan, idx_valid, index, base

    @classmethod
    def _get_segment_index_and_parameter(cls, index, x_in, x_out):
        """ Get segment index and normalized parameter (values from [0, 1] interval) """
        assert index.size > 1

        def _find_indices(x_in, i_in, x_out):
            options = {
                "kind": "linear",
                "fill_value": "extrapolate",
                "bounds_error": False,
                "copy": False,
            }
            if scipy.__version__ >= "0.14":
                options["assume_sorted"] = True
            return interp1d(x_in, i_in, **options)(x_out)

        decimal_index = _find_indices(x_in, index, x_out)

        floor_index = clip(floor(decimal_index), index[0], index[-2])

        return floor_index.astype("int64"), decimal_index - floor_index


class Linear1DInterpolator(BaseSpline1DInterpolator):
    """ Linear 1D interpolator. """

    def __init__(self, x_src, x_dst, gap_threshold=inf, segment_neighbourhood=0):
        gap_threshold = max(0, gap_threshold)
        segment_neighbourhood = max(0, segment_neighbourhood)
        self.x_dst_shape = x_dst.shape
        self.idx_nan, self.idx_valid, self.index, self.base = self._get_indices(
            x_src, x_dst, gap_threshold,
            segment_neighbourhood, segment_neighbourhood,
        )

    def __call__(self, y_src, dy_src=None):
        del dy_src
        y_dst = empty(self.x_dst_shape[:1] + y_src.shape[1:])
        if y_dst.size > 0:
            y_dst[self.idx_nan] = nan
            # expand_dim requires NumPy >= v1.8.0
            extra_dims = tuple(range(2, y_src.ndim + 1))
            y_dst[self.idx_valid] = (
                expand_dims(self.base, axis=extra_dims) * y_src[self.index]
            ).sum(axis=1)
        return y_dst


class Cubic1DInterpolator(BaseSpline1DInterpolator):
    """ Cubic Hermit spline 1D interpolator. """

    @staticmethod
    def _get_hermit_spline_basis(x_src, index, base):
        a1, b1 = base[:, 0], base[:, 1]
        a2, b2 = a1*a1, b1*b1
        dx = (x_src[1:] - x_src[:-1])[index[:, 0]]

        return (
            stack(((1 + 2*b1) * a2, (1 + 2*a1) * b2), axis=1),
            stack((b1 * a2 * dx, -a1 * b2 * dx), axis=1)
        )

    def __init__(self, x_src, x_dst, gap_threshold=inf, segment_neighbourhood=0):
        gap_threshold = max(0, gap_threshold)
        segment_neighbourhood = max(0, segment_neighbourhood)
        self.x_dst_shape = x_dst.shape
        self.idx_nan, self.idx_valid, self.index, base = self._get_indices(
            x_src, x_dst, gap_threshold,
            segment_neighbourhood, segment_neighbourhood,
        )
        self.base0, self.base1 = self._get_hermit_spline_basis(
            x_src, self.index, base
        )

    def __call__(self, y_src, dy_src=None):
        y_dst = empty(self.x_dst_shape[:1] + y_src.shape[1:])
        if y_dst.size > 0:
            y_dst[self.idx_nan] = nan
            # expand_dim requires NumPy >= v1.8.0
            extra_dims = tuple(range(2, y_src.ndim + 1))
            y_dst[self.idx_valid] = (
                expand_dims(self.base0, axis=extra_dims) * y_src[self.index]
            ).sum(axis=1) + (
                expand_dims(self.base1, axis=extra_dims) * dy_src[self.index]
            ).sum(axis=1)
        return y_dst


def _generate_contigous_segments(x_src, x_dst, gap_threshold,
                                 lower_neighbourhood, upper_neighbourhood):
    """ Generator yielding contiguous data ranges. """
    # process x_src contiguous ranges
    for idx_src_low, idx_src_high in _generate_contiguous_ranges(x_src, gap_threshold):
        x_l = x_src[idx_src_low] - lower_neighbourhood
        x_h = x_src[idx_src_high-1] + upper_neighbourhood
        # get range of the x_dst overlapping the x_src segment
        idx_dst_low = searchsorted(x_dst, x_l, side="left")
        idx_dst_high = searchsorted(x_dst, x_h, side="right")
        if idx_dst_high > idx_dst_low:
            yield (
                (x_l, x_h),
                (idx_src_low, idx_src_high),
                (idx_dst_low, idx_dst_high),
            )


def _generate_contiguous_ranges(x_src, gap_threshold):
    """ Generator yielding contiguous ranges of the interpolated variable. """
    idx_low = 0
    for idx_high in (diff(x_src) > gap_threshold).nonzero()[0] + 1:
        yield idx_low, idx_high
        idx_low = idx_high
    idx_high = len(x_src)
    if idx_high > 0:
        yield idx_low, idx_high


def _get_nan_mask(index):
    """ Get indices of the valid and NaN values. """
    is_nan = isnan(index)
    return is_nan.nonzero()[0], invert(is_nan).nonzero()[0]
