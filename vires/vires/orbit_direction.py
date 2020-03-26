#-------------------------------------------------------------------------------
#
# Orbit direction file handling
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments

from numpy import abs as aabs, asarray, searchsorted
from .aux_common import CdfEpochTimeMixIn, BaseReader


class OrbitDirectionReader(CdfEpochTimeMixIn, BaseReader):
    """ Orbit direction data reader class. """
    TIME_FIELD = "Timestamp"
    DATA_FIELDS = ("OrbitDirection", "BoundaryType")
    TYPES = {"OrbitDirection": "int8", "BoundaryType": "int8"}
    NODATA = {"OrbitDirection": 0, "BoundaryType": -1}
    INTERPOLATION_KIND = "zero"

    def _update_product_set(self, cdf, start, end):

        def _read_time_ranges(attr):
            attr._raw = True               # pylint: disable=protected-access
            return asarray(list(attr))

        def _add_overlap(starts, ends, distance, overlap):
            idx, = (aabs((starts - ends) - distance) < 5.).nonzero()
            ends[idx] += overlap
            starts[idx] -= overlap

        def _find_subset(starts, ends, start, end, margin=0, offset=0):
            return (
                max(0, searchsorted(ends, start, 'left') - margin) + offset,
                searchsorted(starts, end, 'right') + margin + offset
            )

        neighbour_distance = cdf.attrs['NEIGHBOUR_DISTANCE']
        neighbour_overlap = cdf.attrs['NEIGHBOUR_OVERLAP']
        ranges = _read_time_ranges(cdf.attrs['SOURCE_TIME_RANGES'])

        # find first rough subset with margin
        idx_start, idx_stop = _find_subset(
            ranges[:, 0], ranges[:, 1], start, end, margin=1
        )
        ranges_subset = ranges[idx_start:idx_stop, :]

        # add the temporal overlaps
        _add_overlap(
            ranges_subset[1:, 0], ranges_subset[:-1, 1],
            neighbour_distance, neighbour_overlap
        )

        # find the final exact subset
        idx_start, idx_stop = _find_subset(
            ranges_subset[:, 0], ranges_subset[:, 1], start, end,
            offset=idx_start
        )
        self.product_set.update(cdf.attrs['SOURCES'][idx_start:idx_stop])
