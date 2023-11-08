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
# pylint: disable=too-many-arguments,too-few-public-methods,

from os.path import exists
from collections import namedtuple
from numpy import (
    nan, inf, abs as aabs, array, asarray, searchsorted, concatenate,
)
from ..aux_common import (
    CdfEpochTimeMixIn, BaseReader,
    subset_time, interpolate_time,
)
from ..file_util import FileChangeMonitor
from ..cdf_util import cdf_open, CDF_EPOCH_TYPE, CDF_TYPE_TO_LABEL
from .common import FLAG_START, FLAG_END
from .merge import resolve_overlaps


SOURCE_TIME_RANGES_ATTR = "SOURCE_TIME_RANGES"
SOURCES_ATTR = "SOURCES"
NEIGHBOUR_DISTANCE_ATTR = "NEIGHBOUR_DISTANCE"
NEIGHBOUR_OVERLAP_ATTR = "NEIGHBOUR_OVERLAP"

TIME_TYPE = CDF_EPOCH_TYPE
TIME_FIELD = "Timestamp"
ORBIT_DIRECTION_FIELD = "OrbitDirection"
BOUNDARY_TYPE_FIELD = "BoundaryType"
TYPES = {
    ORBIT_DIRECTION_FIELD: "int8",
    BOUNDARY_TYPE_FIELD: "int8",
}
NODATA = {
    ORBIT_DIRECTION_FIELD: 0,
    BOUNDARY_TYPE_FIELD: -1,
}
INTERPOLATION_KIND = "previous"


class OrbitDirectionReader(CdfEpochTimeMixIn, BaseReader):
    """ Orbit direction data reader class. """
    TIME_FIELD = TIME_FIELD
    DATA_FIELDS = (ORBIT_DIRECTION_FIELD, BOUNDARY_TYPE_FIELD)
    TYPES = TYPES
    NODATA = NODATA
    INTERPOLATION_KIND = INTERPOLATION_KIND

    def __init__(self, *filenames, product_set=None):
        super().__init__(product_set=product_set)
        self._filenames = filenames
        self._file_monior = FileChangeMonitor()
        self._data = None

    def read_data(self):
        """ Read cached orbit direction lookup tables.
        Non-existing files are skipped.
        """
        if self._file_monior.changed(*self._filenames) or self._data is None:
            self._data = _ODTable.read_from_files(*self._filenames)
        return self._data

    def _subset(self, start, stop, time_field, fields, types, **options):
        data = self.read_data()
        result = subset_time(
            source=data.get_data,
            start=start,
            stop=stop,
            time_field=time_field,
            fields=fields,
            **options
        )
        self.product_set.update(data.get_sources(start, stop))
        return result

    def _interpolate(self, time, time_field, fields, types, kind, nodata):
        data = self.read_data()
        result = interpolate_time(
            source=data.get_data,
            time=time,
            time_field=time_field,
            fields=fields,
            types=types,
            nodata=nodata,
            kind=kind,
        )
        if time.size > 0:
            self.product_set.update(data.get_sources(time.min(), time.max()))
        return result


class _ODTable(CdfEpochTimeMixIn):
    variable_mapping = {
        TIME_FIELD: lambda obj: obj.times,
        ORBIT_DIRECTION_FIELD: lambda obj: obj.orbit_directions,
        BOUNDARY_TYPE_FIELD: lambda obj: obj.boundary_types,
    }

    def __init__(self, times, orbit_directions, boundary_types,
                 sources, source_time_ranges, start=None, end=None):
        self.times = times
        self.orbit_directions = orbit_directions
        self.boundary_types = boundary_types
        self.sources = sources
        self.source_time_ranges = source_time_ranges
        self.start = start if start is not None else (
            self.times[0] if times.size > 0 else nan
        )
        self.end = end if end is not None else (
            self.times[-1] if times.size > 0 else nan
        )

    @property
    def is_empty(self):
        """ True if the orbit direction table is empty. """
        return self.times.size == 0

    @classmethod
    def create_empty(cls):
        """ Create an empty orbit direction table. """
        def _get_empty_array(variable):
            return array([], TYPES.get(variable))
        return cls(
            times=_get_empty_array(TIME_FIELD),
            orbit_directions=_get_empty_array(ORBIT_DIRECTION_FIELD),
            boundary_types=_get_empty_array(BOUNDARY_TYPE_FIELD),
            sources=[],
            source_time_ranges=[],
        )

    @classmethod
    def read_from_files(cls, *filenames):
        """ Read orbit direction table from multiple CDF files. """
        return cls.merge(*[
            cls.read_from_file(filename) for filename in filenames
        ])

    @classmethod
    def read_from_file(cls, filename):
        """ Read orbit direction table from a CDF file. """

        def _check_timestamp_type(cdf_type):
            if cdf_type != TIME_TYPE:
                raise TypeError(
                    f"Unexpected {TIME_FIELD} data type "
                    f"{CDF_TYPE_TO_LABEL[cdf_type]}!"
                )

        def _read_data(cdf, variable):
            return cdf.raw_var(variable)[...]

        def _read_option(cdf, attr_name):
            return float(cdf.attrs[attr_name][0])

        def _read_source_time_ranges(cdf, attr_name):
            attr = cdf.attrs[attr_name]
            attr._raw = True               # pylint: disable=protected-access
            return asarray(list(attr))

        def _read_sources(cdf, attr_name):
            return list(cdf.attrs[attr_name])

        def _add_buffer_to_time_ranges(ranges, neighbour_distance,
                                       neighbour_overlap):
            mask = _find_overlaps(ranges[1:, 0], ranges[:-1, 1], neighbour_distance)
            _add_overlap_buffer(ranges[1:, 0], ranges[:-1, 1], mask, neighbour_overlap)
            _add_end_buffer(ranges[:, 1], ~mask, neighbour_distance)
            return ranges

        def _find_overlaps(starts, ends, distance):
            threshold = 5. # milliseconds, CDF_EPOCH
            return aabs((starts - ends) - distance) < threshold

        def _add_overlap_buffer(starts, ends, selection, overlap):
            ends[selection] += overlap
            starts[selection] -= overlap

        def _add_end_buffer(ends, selection, distance):
            ends[:-1][selection] += distance
            if ends.size > 0:
                ends[-1] += distance

        if not exists(filename):
            return cls.create_empty()

        with cdf_open(filename) as cdf:
            _check_timestamp_type(cdf.raw_var(TIME_FIELD).type())
            return cls(
                times=_read_data(cdf, TIME_FIELD),
                orbit_directions=_read_data(cdf, ORBIT_DIRECTION_FIELD),
                boundary_types=_read_data(cdf, BOUNDARY_TYPE_FIELD),
                sources=_read_sources(cdf, SOURCES_ATTR),
                source_time_ranges=_add_buffer_to_time_ranges(
                    _read_source_time_ranges(cdf, SOURCE_TIME_RANGES_ATTR),
                    neighbour_distance=_read_option(cdf, NEIGHBOUR_DISTANCE_ATTR),
                    neighbour_overlap=_read_option(cdf, NEIGHBOUR_OVERLAP_ATTR),
                )
            )

    @classmethod
    def merge(cls, *od_tables):
        """ Merge multiple od_tables into one. """

        od_tables = [item for item in od_tables if not item.is_empty]

        if len(od_tables) == 0:
            return cls.create_empty()

        if len(od_tables) == 1:
            return od_tables[0]

        #print(od_tables)
        return cls.join(*cls.resolve_overlaps(*od_tables))

    @classmethod
    def resolve_overlaps(cls, *od_tables):
        """ Resolve overlapped od_tables into a sequence of non-overlapping ones. """
        return resolve_overlaps(
            [od_table.split_to_segments() for od_table in od_tables]
        )

    @classmethod
    def join(cls, *od_tables):
        """ Join multiple od_tables into one. """
        od_tables = [item for item in od_tables if not item.is_empty]

        if len(od_tables) == 0:
            return cls.create_empty()

        if len(od_tables) == 1:
            return od_tables[0]

        times = []
        orbit_directions = []
        boundary_types = []
        sources = []
        source_time_ranges = []

        last_item = None
        for item in od_tables:
            times.append(item.times)
            orbit_directions.append(item.orbit_directions)
            boundary_types.append(item.boundary_types)
            sources.extend(item.sources)
            source_time_ranges.append(item.source_time_ranges)
            # sanity check
            if last_item:
                if last_item.times[-1] > item.times[0]:
                    raise ValueError("Data timestamps not ordered in time!")
                if (last_item.source_time_ranges[-1] > item.source_time_ranges[0]).any():
                    raise ValueError("Sources' timestamps not ordered in time!")
            last_item = item

        return cls(
            times=concatenate(times),
            orbit_directions=concatenate(orbit_directions),
            boundary_types=concatenate(boundary_types),
            sources=sources,
            source_time_ranges=concatenate(source_time_ranges)
        )

    def get_data(self, field, slice_=None):
        """ Read data array by variable. """
        return self.variable_mapping[field](self)[slice_ or Ellipsis]

    def interpolate(self, time, fields, types, nodata, min_len=2, **options):
        """ Interpolate the requested fields at the given time values.
        Data exceeding the time interval of the source data is filled with the
        `nodata` dictionary. The function accepts additional keyword arguments
        which are passed to the `scipy.interpolate.interp1d` function
        (e.g., `kind`).
        """
        return interpolate_time(
            source=self.get_data,
            time=time,
            time_field=TIME_FIELD,
            fields=fields,
            types=types,
            nodata=nodata,
            bounds=None,
            min_len=min_len,
            **options
        )

    def get_sources(self, start, end):
        """ Get sources matched_by the time-interval. """
        return self.sources[self._get_sources_slice(start, end)]

    def split_to_segments(self):
        """ Split to list of new object, one for each contiguous segments. """
        def _extract_subset(idx_first, idx_last):
            data_slice = slice(idx_first, idx_last+1)
            times = self.times[data_slice]
            sources_slice = (
                self._get_sources_slice(times[0], times[-1])
                if times.size > 0 else slice(0, 0)
            )
            return self._subset(data_slice, sources_slice)

        return [
            _extract_subset(idx_start, idx_stop)
            for idx_start, idx_stop in self._find_contiguous_segments()
        ]

    def trim(self, start=+inf, end=-inf):
        """ Get copy with trimmed time extent. """
        if start <= self.start and self.end < end:
            data_slice = slice(None, None)
            sources_slice = slice(None, None)
        else:
            data_slice = self._get_data_slice(start, end)
            sources_slice = self._get_sources_slice(start, end)

        data = self._subset(
            data_slice,
            sources_slice,
            start=(start if start > -inf else None),
            end=(end if end < +inf else None),
        )
        data.source_time_ranges = self._trim_time_ranges(
            data.source_time_ranges.copy(), start, end
        )
        return data

    @staticmethod
    def _trim_time_ranges(time_ranges, start, end):
        """ Trim the source time ranges to not exceed the given time interval.
        """
        starts = time_ranges[:, 0]
        ends = time_ranges[:, 1]
        starts[starts < start] = start
        ends[ends > end] = end
        return time_ranges

    def _find_contiguous_segments(self):
        """ Return indices for starts and ends of the contiguous segments. """
        idx_start = (self.boundary_types == FLAG_START).nonzero()[0]
        idx_end = (self.boundary_types == FLAG_END).nonzero()[0]

        # basic sanity check
        if (
            idx_start.shape != idx_end.shape or
            (idx_start > idx_end).any() or
            (idx_start[1:] < idx_end[:-1]).any()
        ):
            raise ValueError("Segments boundaries not ordered!")

        return zip(idx_start, idx_end)

    def _subset(self, data_slice, sources_slice, **options):
        return self.__class__(
            times=self.times[data_slice],
            orbit_directions=self.orbit_directions[data_slice],
            boundary_types=self.boundary_types[data_slice],
            sources=self.sources[sources_slice],
            source_time_ranges=self.source_time_ranges[sources_slice],
            **options
        )

    def _get_sources_slice(self, start, end):
        """ Return slice selecting subset of the sources matched by the
        given start and end times.
        """
        starts = self.source_time_ranges[:, 0]
        ends = self.source_time_ranges[:, 1]
        return slice(
            searchsorted(ends, start, "left"),
            #searchsorted(starts, end, "right")  # end time included
            searchsorted(starts, end, "left")  # end time excluded
        )

    def _get_data_slice(self, start, end):
        """ Return slice selecting subset of the data matched by the
        given start and end times.
        """
        return slice(
            searchsorted(self.times, start, "left"),
            #searchsorted(self.times, end, "right")  # end time included
            searchsorted(self.times, end, "left")  # end time excluded
        )
