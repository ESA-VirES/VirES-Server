#-------------------------------------------------------------------------------
#
#  Calculation of finite differences approximation of first derivatives.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

from numpy import asarray, empty, nan, inf, diff


def get_slopes_from_nodes(x, y, fill_border_values=False, gap_threshold=inf):
    """ Get estimate of the function first derivative from given locations
    and function values using the general finite difference formula.

    Returns:
        N estimated slope values at the (shape: N + Y-trailing shape)

    Args:
        x - N nodes locations (sorted, distinct, possibly non-equidistant, shape: N)
        y - N interpolated values at the (shape: N + Y-trailing shape)
        fill_border_values - if set to True slope estimates for the border
            values will be calculated.
        gap_threshold - minimum x distance interpreted as a gap.
    """
    yd1 = empty(y.shape)
    for idx_low, idx_high in generate_contiguous_ranges(x, gap_threshold):
        if idx_high - idx_low < 2: # filter out short segments
            yd1[idx_low:idx_high] = nan
        else:
            yd1[idx_low:idx_high] = _get_slopes_from_nodes(
                x[idx_low:idx_high],
                y[idx_low:idx_high],
                fill_border_values=fill_border_values
            )
    return yd1


def generate_contiguous_ranges(x, gap_threshold):
    """
    Generate indices of continuous data ranges.

    Yields:
        tuples of minimum and maximum selection index for each continuous
        range.

    Args:
        x - N nodes locations (sorted, distinct, possibly non-equidistant, shape: N)
        gap_threshold - minimum x distance interpreted as a gap.
    """
    dx = diff(x)
    if dx.size > 0 and dx.min() <= 0.0:
        raise ValueError("X values must be distinct and sorted!")
    idx_low = 0
    for idx_high in (dx > gap_threshold).nonzero()[0] + 1:
        yield idx_low, idx_high
        idx_low = idx_high
    idx_high = len(x)
    if idx_high > 0:
        yield idx_low, idx_high


def _get_slopes_from_nodes(x, y, fill_border_values=False):
    x = asarray(x)
    y = asarray(y)

    assert x.ndim == 1
    assert y.shape[0] == x.shape[0]

    # reshape shortcut
    def r(v):
        return v.reshape((*v.shape, *(1,)*(y.ndim - v.ndim)))

    dx = x[1:] - x[:-1]
    dy = (y[1:] - y[:-1]) / r(dx)

    #if dx.min() > 0.0:
    #    raise ValueError("X values must be distinct and sorted!")

    yd1 = empty(y.shape)
    yd1[1:-1] = (r(dx[1:])*dy[:-1] + r(dx[:-1])*dy[1:]) / r(dx[:-1] + dx[1:])
    yd1[[0, -1]] = dy[[0, -1]] if fill_border_values else nan

    return yd1
