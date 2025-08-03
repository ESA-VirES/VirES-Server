#
# Piecewise polynomial interpolation
#
from numpy import (
    asarray,
    empty,
    zeros,
    ones,
    stack,
    concatenate,
    expand_dims,
    searchsorted,
)
from numpy.lib.stride_tricks import as_strided


def eval_spline(x, nodes, coeff):
    """ Evaluate splines at the given locations.

    x values outside the [nodes[0], nodes[-1]] interval are extrapolated
    from the first or last polynomial.

    Returns:
        y - spline evalueted for the given x locations (shape: X-shape + Y-trailing shape)

    Args:
        x - locations (shape: any)
        nodes - N nodes locations (sorted, distinct, non-equidistant, shape: N)
        coeff - N x M array of coefficients (shape: N x M + Y-trailing shape)
            the last coeficients extrapolate the spline of the (N-1)th interval.
    """
    assert nodes.ndim == 1
    assert coeff.ndim >= 2
    assert coeff.shape[0] == nodes.shape[0]

    if coeff.shape[1] == 0:
        return zeros(x.shape)

    idx = (searchsorted(nodes, x, side="right") - 1).clip(0, nodes.size - 2)

    dx = (x - nodes[idx]).reshape((*x.shape, *(1,)*(coeff.ndim - 2)))

    y = coeff[idx, -1, ...]
    for i in range(2, coeff.shape[1] + 1):
        y = coeff[idx, -i, ...] + dx * y

    return y


def differentiate_spline(coeff):
    """ Differentiate piecewise polynomial spline.

    Returns:
        coeff - N x (M-1) array of coefficients (shape: N x (M-1) + Y-trailing shape)

    Args:
        coeff - N x M array of coefficients (shape: N x M + Y-trailing shape)
    """
    coeff = coeff[:, 1:, ...].copy()
    for idx in range(1, coeff.shape[1]):
        coeff[:, idx, ...] *= (idx + 1)
    return coeff


def get_piecewise_cubic_spline(x, y, yd1):
    """ Get piecewise quadratic spline coefficinets interpolating the given values
    and slopes.

    Returns:
        coeff - N x 4 array of coefficients (shape: N x 4 + Y-trailing shape)
            the last coeficients extrapolate the spline of the (N-1)th interval.

    Args:
        x - N nodes locations (sorted, distinct, possibly non-equidistant, shape: N)
        y - N interpolated values at the (shape: N + Y-trailing shape)
        yd1 - N interpolated slopes at the (shape: N + Y-trailing shape)
    """
    x = asarray(x)
    y = asarray(y)
    yd1 = asarray(yd1)

    assert x.ndim == 1
    assert y.shape[0] == x.shape[0]
    assert y.shape == yd1.shape

    node_values = restride_to_intervals(y, step=1)
    node_slopes = restride_to_intervals(yd1, step=1)

    # calculate the divided differences
    nodes, dd = calculate_divided_differences(
        restride_to_intervals(x, step=1),
        stack((
            node_values[:, 0, ...],
            node_slopes[:, 0, ...],
            node_values[:, 1, ...],
            node_slopes[:, 1, ...],
        ), axis=1),
        [2, 2],
    )
    for _ in range(2):
        nodes, dd = add_point_to_divided_difference(nodes[..., 0], nodes, dd)

    # handle last point (extrapolation from the last interval)
    last_node = x[-1]
    nodes_last, dd_last = nodes[-1, ...], dd[-1, ...]
    for _ in range(4):
        nodes_last, dd_last = add_point_to_divided_difference(
            last_node, nodes_last, dd_last
        )

    # append last point
    dd = concatenate((dd, dd_last.reshape((1, *dd_last.shape))), axis=0)

    # return spline coefficients
    return dd[:, 0, ...]


def get_piecewise_linear_spline(x, y):
    """ Get coefficients of a piecewise linear spline coefficinets interpolating the given values.

    Returns:
        coeff - N x 2 array of coefficients (shape: N x 2 + Y-trailing shape)
            the last coeficients extrapolate the spline of the (N-1)th interval.

    Args:
        x - N nodes locations (sorted, distinct, possibly non-equidistant, shape: N)
        y - N interpolated values at the (shape: N + Y-trailing shape)
    """
    x = asarray(x)
    y = asarray(y)

    assert x.ndim == 1
    assert y.shape[0] == x.shape[0]

    # calculate the divided differences
    nodes, dd = calculate_divided_differences(
        restride_to_intervals(x, step=1),
        restride_to_intervals(y, step=1),
    )
    nodes, dd = add_point_to_divided_difference(nodes[..., 0], nodes, dd)

    # handle last point (extrapolation from the last interval)
    last_node = x[-1]
    nodes_last, dd_last = nodes[-1, ...], dd[-1, ...]
    for _ in range(2):
        nodes_last, dd_last = add_point_to_divided_difference(
            last_node, nodes_last, dd_last
        )

    # append last point
    dd = concatenate((dd, dd_last.reshape((1, *dd_last.shape))), axis=0)

    # return spline coefficients
    return dd[:, 0, ...]


def get_slopes_from_nodes(x, y):
    """ Get estimate of the function first derivative from given locations and function
    values using the finite difference formula.

    Returns:
        N estimated slope values at the (shape: N + Y-trailing shape)

    Args:
        x - N nodes locations (sorted, distinct, possibly non-equidistant, shape: N)
        y - N interpolated values at the (shape: N + Y-trailing shape)
    """
    x = asarray(x)
    y = asarray(y)

    assert x.ndim == 1
    assert y.shape[0] == x.shape[0]

    # reshape shortcut
    def r(v):
        return v.reshape((*v.shape, *(1,)*(y.ndim - v.ndim)))

    dx = x[1:] - x[:-1]
    dy = (y[1:] - y[:-1]) / r(dx)

    yd1 = zeros(y.shape)
    yd1[1:-1] = (r(dx[1:])*dy[:-1] + r(dx[:-1])*dy[1:]) / r(dx[:-1] + dx[1:])
    yd1[[0, -1]] = dy[[0, -1]]

    return yd1


def calculate_divided_differences(x, y, n=None):
    """ Calculate table of divided differences with a point multiplicity.

    For each node derivatives up to the multiplicity must be provided.
    E.g.,

      x = [x1, x2, x3]
      n = [2, 3, 1] #
      y = [
          y(x1), y'(x1),          # multiplicity 2 - function value + 1st derivative
          y(x2), y'(x2), y''(x2), # multiplicity 3 - function value + 1st and 2nd derivatives
          y(x3),                  # multiplicity 1 - function value only
      ]

    Returns:
        nodes - N array of the nodes (shape: arbitrary X-leading shape + M as the last dimenstion)
        divdiff - M x M upper triangular matrix of divided differences. (shape: arbitrary X-leading
            shape + M x M + arbitrary Y-trailing shape)

    Args:
        x - N nodes (not repeated; arbitrary X-leading shape + N as the last dimenstion)
        y - M function and derivatives values (M = sum(n)) to be filled in the divided differences
            table (shape: arbitrary X-leading shape + M + arbitrary Y-trailing shape)
        n - N integer node mutiplicities, defaults to ones(N)
    """
    # pylint: disable=unnecessary-dunder-call, too-many-locals
    x = asarray(x)
    y = asarray(y)

    if n is None:
        n = ones(x.shape[-1], "int")
    else:
        n = asarray(n)

    x_size = x.shape[-1]
    y_size = y.shape[x.ndim-1]

    assert x.shape[:-1] == y.shape[:x.ndim-1]
    assert n.min() > 0
    assert n.size == x_size
    assert sum(n) == y_size

    # broadcasting helpers
    head_slice = (slice(None, None),) * (x.ndim - 1)
    trailing_slice = (Ellipsis,)
    trailing_ones = (1,) * (y.ndim - x.ndim)

    def _get_dd_slice(i, j):
        return (*head_slice, i, j, *trailing_slice)

    def _get_x_slice(i):
        return (*head_slice, i)

    def _get_y_slice(i):
        return (*head_slice, i, *trailing_slice)

    # allocate output arrays
    nodes = empty((*x.shape[:-1], y_size))
    divdiff = zeros((*x.shape[:-1], y_size, y_size, *y.shape[x.ndim:]))

    # fill the initial level
    offset = 0
    for x_idx in range(x_size):
        count = n[x_idx]
        x_value = x.__getitem__(_get_x_slice(x_idx))
        y_value = y.__getitem__(_get_y_slice(offset))
        for _ in range(count):
            nodes.__setitem__(_get_x_slice(offset), x_value)
            divdiff.__setitem__(_get_dd_slice(offset, offset), y_value)
            offset += 1

    def _divided_difference(level, offset):
        """ Calculate single divided difference """
        dy_value = (
            divdiff.__getitem__(_get_dd_slice(offset + 1, offset + level)) -
            divdiff.__getitem__(_get_dd_slice(offset, offset + level - 1))
        )
        dx_value = (
            nodes.__getitem__(_get_x_slice(offset + level)) -
            nodes.__getitem__(_get_x_slice(offset))
        )
        return dy_value / dx_value.reshape((*dx_value.shape, *trailing_ones))

    # fill the remaning levels
    scale = 1.0
    for level in range(1, y_size):
        scale /= level # reciprocal factorial
        offset = 0
        for x_idx in range(x_size):
            count = min(n[x_idx], y_size - level - offset)
            count_filled = max(0, n[x_idx] - level)
            if count_filled > 0:
                # values filled from the provided derivatives
                value = scale * y.__getitem__(_get_y_slice(offset + level))
                for _ in range(count_filled):
                    divdiff.__setitem__(_get_dd_slice(offset, offset + level), value)
                    offset += 1
            for _ in range(count_filled, count):
                # value calculated
                value = _divided_difference(level, offset)
                divdiff.__setitem__(_get_dd_slice(offset, offset + level), value)
                offset += 1
            if offset >= y_size - level:
                break

    return nodes, divdiff


def add_point_to_divided_difference(x, nodes, divdiff):
    """ Prepend a new point to a table of divided differences.

    Returns:
        nodes - N updated array of the nodes (shape: arbitrary X-leading shape + M as the last
            dimenstion)
        divdiff - M x M updated upper triangular matrix of divided differences. (shape: arbitrary
            X-leading shape + M x M + arbitrary Y-trailing shape)

    Args:
        x - new node to be added
        nodes - N array of the nodes (shape: arbitrary X-leading shape + M as the last dimenstion)
        divdiff - M x M upper triangular matrix of divided differences. (shape: arbitrary X-leading
            shape + M x M + arbitrary Y-trailing shape)
    """
    # pylint: disable=unnecessary-dunder-call
    x = asarray(x)
    nodes = asarray(nodes)
    divdiff = asarray(divdiff)

    size = nodes.shape[-1]

    assert x.shape == nodes.shape[:-1]
    assert divdiff.shape[:nodes.ndim - 1] == nodes.shape[:-1]
    assert divdiff.shape[nodes.ndim - 1:nodes.ndim + 1] == (size, size)

    if size == 0:
        return nodes, divdiff

    # broadcasting helpers
    head_slice = (slice(None, None),) * x.ndim
    trailing_slice = (Ellipsis,)
    trailing_ones = (1,) * (divdiff.ndim - nodes.ndim - 1)

    def _get_dd_slice(i, j):
        return (*head_slice, i, j, *trailing_slice)

    divdiff_new = zeros(divdiff.shape)
    value = divdiff.__getitem__(_get_dd_slice(0, -1))
    divdiff_new.__setitem__(_get_dd_slice(0, -1), value)

    value = divdiff.__getitem__(_get_dd_slice(slice(None, -1), slice(None, -1)))
    divdiff_new.__setitem__(_get_dd_slice(slice(1, None), slice(1, None)), value)

    divdiff = divdiff_new

    for idx in range(size-2, -1, -1):
        value = (
            divdiff.__getitem__(_get_dd_slice(1, idx + 1)) +
            divdiff.__getitem__(_get_dd_slice(0, idx + 1)) *
            (x - nodes[..., idx]).reshape((*x.shape, *trailing_ones))
        )
        divdiff.__setitem__(_get_dd_slice(0, idx), value)

    nodes = concatenate((expand_dims(x, axis=-1), nodes[..., :-1]), axis=-1)

    return nodes, divdiff


def restride_to_intervals(x, step=1):
    """ Restride given sorted to intervals along the first dimenstion,
    each having the given number of steps.

    Returns:
        (N-1)/step x (step + 1) + trailing shape array

    Args:
        x N + trailing shape array
        steps integer number of steps (steps >= 1)
    """
    assert step >= 1
    assert x.ndim >= 1
    return as_strided(
        x,
        shape=((x.shape[0] - 1) // step, step + 1, *x.shape[1:]),
        strides=(x.strides[0]*step, x.strides[0], *x.strides[1:])
    )
