#-------------------------------------------------------------------------------
#
#  Data filters - common utilities
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

from numpy import empty, concatenate, unique
from .exceptions import FilterError


def merge_indices(*indices):
    """ Merge indices eliminating duplicate values. """
    indices = [index for index in indices if index is not None]
    if len(indices) > 1:
        return unique(concatenate(indices))
    if len(indices) == 1:
        return indices[0]
    return empty(0, dtype='int64')


def format_variable(name, index):
    """ Format variable name an index. """
    if index:
        index = ",".join(str(value) for value in index)
        name = f"{name}[{index}]"
    return name


def get_data(dataset, variable, index=None):
    """ Extract filtered data from the given dataset. """
    try:
        data = dataset[variable]
    except KeyError:
        raise FilterError(
            f"Variable {format_variable(variable, index)} does not exist!"
        ) from None

    if index:
        if data.ndim != len(index) + 1:
            if data.ndim == 1:
                raise FilterError(
                    f"The index of {format_variable(variable, index)} "
                    "cannot be applied to scalar data!"
                )
            raise FilterError(
                f"The index of {format_variable(variable, index)} "
                f"does not match the array dimentsion ({data.ndim-1})!"
            )
    elif data.ndim != 1:
        raise FilterError(
            "Scalar filters cannot be applied to a non-scalar "
            f"variable {variable}!"
        )

    selection = (slice(None), *(index or ()))

    try:
        return data[selection]
    except IndexError:
        shape = ",".join(str(size) for size in data.shape[1:])
        raise FilterError(
            f"Index of {format_variable(variable, index)} "
            f"exceeds the array size ({shape})!"
        ) from None
