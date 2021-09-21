#-------------------------------------------------------------------------------
#
# CDF time-series reader
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020 EOX IT Services GmbH
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

from numpy import searchsorted
from .dataset import Dataset
from .cdf_util import CDF_EPOCH_TYPE
from .cdf_write_util import CdfTypeEpoch

DEF_CDF_TYPE_DECODER = lambda data: data
CDF_TYPE_DECODER = {
    CDF_EPOCH_TYPE: CdfTypeEpoch.decode,
}


def get_cdf_type_decoder(cdf_type):
    """ Get CDF type decoder. """
    return CDF_TYPE_DECODER.get(cdf_type, DEF_CDF_TYPE_DECODER)


def read_cdf_time_series(cdf, variables, time_slice=None,
                         time_variable='Timestamp'):
    """ Read time-series subset from a CDF file. """
    if time_slice:
        dataset = read_cdf_data(cdf, [time_variable])
        slice_ = time_slice(dataset[time_variable])
    else:
        slice_ = Ellipsis
    return read_cdf_data(cdf, variables, slice_=slice_)


def read_cdf_data(cdf, variables, slice_=Ellipsis):
    """ Read data from a CDF file. """
    dataset = Dataset()

    if isinstance(slice_, (type(Ellipsis), slice)):
        index = Ellipsis
    else:
        slice_, index = Ellipsis, slice_

    for variable in variables:
        cdf_var = cdf.raw_var(variable)
        decode_data = get_cdf_type_decoder(cdf_var.type())
        dataset.set(
            variable, decode_data(cdf_var[slice_][index]),
            cdf_var.type(), cdf_var.attrs,
        )

    return dataset


def sorted_range_slice(start, end, left_closed=True, right_closed=True,
                       right_margin=0, left_margin=0):
    """ Second order function returning sorted range slicer. """

    def _sorted_range(data):
        """ Get a slice of a sorted data array matched by the given interval. """
        idx_start, idx_end = None, None

        if start is not None:
            idx_start = searchsorted(data, start, 'left' if left_closed else 'right')
            if left_margin > 0:
                idx_start = max(0, idx_start - left_margin)

        if end is not None:
            idx_end = searchsorted(data, end, 'right' if right_closed else 'left')
            if right_margin > 0:
                idx_end += right_margin

        return slice(idx_start, idx_end)

    return _sorted_range
