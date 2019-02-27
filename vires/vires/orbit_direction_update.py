#-------------------------------------------------------------------------------
#
# Orbit direction - update of the lookup tables
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=unused-import, missing-docstring

from __future__ import print_function
from os import remove, rename
from os.path import exists, basename
from logging import getLogger
from itertools import chain, izip_longest
from collections import namedtuple
from bisect import bisect_left, bisect_right
from numpy import (
    asarray, datetime64, timedelta64, concatenate, searchsorted, full, dtype,
    empty, int8,
)
from eoxmagmod import mjd2000_to_decimal_year, eval_qdlatlon
from .util import full
from .cdf_util import (
    cdf_open, cdf_time_subset, cdf_time_interp, datetime_to_cdf_rawtime,
    CDF_EPOCH_TYPE,
    CDF_INT1_TYPE,
    GZIP_COMPRESSION,
    GZIP_COMPRESSION_LEVEL1,
    CDF_CREATOR,
)

SAMPLING = timedelta64(1000, 'ms') # sampling step
INPUT_MARGIN = 5 # number of samples needed from the surrounding products
OUTPUT_MARGIN = 3 # output margin as number of samples
MS2DAYS = 1.0/(24*60*60*1e3) # milliseconds to days scale factor
FLAG_START = int8(1)
FLAG_END = int8(-1)
FLAG_MIDDLE = int8(0)
FLAG_ASCENDING = int8(1)
FLAG_DESCENDING = int8(-1)
FLAG_UNDEFINED = int8(0)

FLAGS_ORBIT_DIRECTION = asarray([FLAG_DESCENDING, FLAG_ASCENDING], 'int8')

LABEL_GEO = "Orbit directions boundaries in geographic coordinates."
LABEL_MAG = "Orbit directions boundaries in quasi-dipole coordinates."

InputData = namedtuple("InputData", ["times", "lats", "lons", "rads"])
OutputData = namedtuple("OutputData", ["times", "odirs", "flags"])
Products = namedtuple("Products", ["names", "start_times", "end_times"])


class DataIntegrityError(ValueError):
    """ Command error exception. """
    pass


class OrbitDirectionTables(object):
    """ Single spacecraft orbit direction lookup tables class. """

    def __init__(self, geo_table_filename, mag_table_filename, reset=False,
                 logger=None):
        self.logger = logger or getLogger(__name__)
        self._geo_table = GeoOrbitDirectionTable(
            geo_table_filename, reset, logger=self.logger
        )
        self._mag_table = QDOrbitDirectionTable(
            mag_table_filename, reset, logger=self.logger
        )

    def __contains__(self, product_id):
        return (
            product_id in self._geo_table and product_id in self._mag_table
        )

    @property
    def changed(self):
        """ Return true if the tables changed and should be saved. """
        return self._geo_table.changed or self._mag_table.changed

    @property
    def products(self):
        """ Iterate products of the lookup table. """
        product_set = set()
        product_set.update(self._geo_table.products)
        product_set.update(self._mag_table.products)
        return product_set

    def save(self):
        """ Save the tables. """
        self._geo_table.save()
        self._mag_table.save()

    def remove(self, product_id):
        """ Remove product from the lookup tables. """
        self._geo_table.remove(product_id)
        self._mag_table.remove(product_id)
        self.logger.info(
            "%s removed from orbit direction lookup tables", product_id
        )

    def update(self, product_id, data_file, data_file_before, data_file_after):
        """ Update orbit direction tables. """
        has_product_before = data_file_before is not None
        has_product_after = data_file_after is not None

        data_items = [load_data_from_product(data_file)]
        start_time, end_time = data_items[0].times[[0, -1]]

        if has_product_before:
            data_items.insert(0, load_data_from_product(
                data_file_before, slice(-INPUT_MARGIN, None)
            ))

        if has_product_after:
            data_items.append(load_data_from_product(
                data_file_after, slice(None, INPUT_MARGIN)
            ))

        data = InputData(*join_data(data_items))

        check_input_data_integrity(
            data,
            start_time - SAMPLING*(INPUT_MARGIN if has_product_before else 0),
            end_time + SAMPLING*(INPUT_MARGIN if has_product_after else 0),
        )

        opts = {
            "has_product_before": has_product_before,
            "has_product_after": has_product_after,
        }

        self._geo_table.update(
            process_variable(*get_times_and_latitudes(*data), **opts),
            product_id, start_time, end_time, SAMPLING * OUTPUT_MARGIN
        )

        self._mag_table.update(
            process_variable(*get_times_and_qd_latitudes(*data), **opts),
            product_id, start_time, end_time, SAMPLING * OUTPUT_MARGIN
        )

        self.logger.info(
            "%s orbit direction lookup tables extracted", product_id
        )


class OrbitDirectionTable(object):
    """ Base orbit direction lookup table class """
    DESCRIPTION = None

    def __init__(self, filename, reset=False, logger=None):
        self._filename = filename
        self._products = None
        self._product_set = None
        self._data = None
        self._changed = None
        self.logger = logger or getLogger(__name__)

        if not reset and exists(filename):
            with cdf_open(filename) as cdf:
                self._load_table(cdf)
        else:
            self._reset_table()

    def __contains__(self, product_id):
        return product_id in self._product_set

    @property
    def changed(self):
        """ Return true if the table is changed and should be saved. """
        return self._changed

    @property
    def products(self):
        """ Iterate products of the lookup table. """
        return set(self._product_set)

    def save(self):
        """ Save tables to a file. """
        self.verify()
        tmp_filename = self._filename + ".tmp.cdf"
        if exists(tmp_filename):
            remove(tmp_filename)
        try:
            with cdf_open(tmp_filename, "w") as cdf:
                self._save_table(cdf)
        except:
            raise
        else:
            rename(tmp_filename, self._filename)
            self.logger.info(
                "%s table saved", self._get_product_id(self._filename)
            )
            self._changed = False
        finally:
            if exists(tmp_filename):
                remove(tmp_filename)

    def remove(self, product_id):
        """ Remove product from the lookup tables. """
        if product_id not in self:
            return
        start_time, end_time = self._remove_product(product_id)
        self._cut_out_data(start_time, end_time)
        self._changed = True

    def update(self, data, product_id, start_time, end_time, margin):
        """ Update orbit direction table file. """
        self._merge_data(data, start_time, end_time, margin)
        self._insert_product(product_id, start_time, end_time)
        self._changed = True

    def dump(self):
        self._dump(self._data)

    @staticmethod
    def _dump(data, prefix=""):
        flag2str = {FLAG_START: "START", FLAG_END: "END", FLAG_MIDDLE: ""}
        odir2str = {
            FLAG_ASCENDING: "A", FLAG_DESCENDING: "D", FLAG_UNDEFINED: "?"
        }
        for time, odir, flag in zip(*data):
            print(prefix, time, odir2str[odir], flag2str[flag])

    def verify(self):
        """ Verify data. """
        times = self._data.times
        pass_flags = self._data.odirs
        type_flags = self._data.flags

        if not (times[1:] > times[:-1]).all():
            raise DataIntegrityError("Times are not strictly increasing!")

        flags = type_flags[type_flags != FLAG_MIDDLE]

        # Every odd is a start. Every even is an end. Starts and ends are paired.
        if (
                (flags[::2] != FLAG_START).any() or
                (flags[1::2] != FLAG_END).any() or
                flags.size % 2 or (type_flags.size and not flags.size)
            ):
            raise DataIntegrityError(
                "Wrong block boundaries! Starts and ends are not alternating."
            )

        idx_start, = (type_flags == FLAG_START).nonzero()
        idx_end, = (type_flags == FLAG_END).nonzero()

        # An end is always followed by a start.
        if ((idx_start[1:] - idx_end[:-1]) != 1).any():
            raise DataIntegrityError(
                "Wrong block boundaries! An end is not followed by a start!"
            )

        for start, stop in zip(idx_start, idx_end):
            # Orbit directions within a block are alternating.
            flags = pass_flags[start:stop]
            if (
                    (flags == FLAG_UNDEFINED).any() or
                    (flags[1:] == flags[:-1]).any()
                ):
                raise DataIntegrityError("Orbit direction do not alternate!")

        self.logger.info(
            "%s table is valid", self._get_product_id(self._filename)
        )

    def _remove_product(self, product_id):
        idx = self._products.names.index(product_id)
        start_time = self._products.start_times[idx]
        end_time = self._products.end_times[idx]
        self._products = Products(*join_lists([
            slice_data(self._products, slice(None, idx)),
            slice_data(self._products, slice(idx + 1, None)),
        ]))
        self._product_set.remove(product_id)
        return start_time, end_time

    def _insert_product(self, product_id, start_time, end_time):
        idx_start = bisect_left(self._products.end_times, start_time)
        idx_end = bisect_right(self._products.start_times, end_time)
        self._products = Products(*join_lists([
            slice_data(self._products, slice(None, idx_start)),
            Products([product_id], [start_time], [end_time]),
            slice_data(self._products, slice(idx_end, None)),
        ]))
        self._product_set.add(product_id)

    @staticmethod
    def _get_product_id(filename):
        return basename(filename).rpartition('.')[0]

    def _merge_data(self, data, start_time, end_time, margin):
        start_trim_time = start_time - margin
        end_trim_time = end_time + margin
        old_data = self._data

        self._data = OutputData(*join_data([
            slice_data(old_data, sorted_range(
                old_data.times, None, start_trim_time, right_closed=False
            )),
            slice_data(data, sorted_range(
                data.times, start_trim_time, end_trim_time
            )),
            slice_data(old_data, sorted_range(
                old_data.times, end_trim_time, None, left_closed=False
            )),
        ]))

    def _cut_out_data(self, start_time, end_time):
        """" Remove data within the given time interval. """

        data_items = [
            OutputData(*slice_data(self._data, sorted_range(
                self._data.times, None, start_time, right_closed=False
            )))
        ]

        data_removed = OutputData(*slice_data(self._data, sorted_range(
            self._data.times, start_time, end_time
        )))

        data_tail = OutputData(*slice_data(self._data, sorted_range(
            self._data.times, end_time, None, right_closed=False
        )))
        if data_tail.flags.size and data_tail.flags[0] == FLAG_END:
            data_tail = OutputData(*slice_data(data_tail, slice(1, None)))

        if data_removed.flags[0] != FLAG_START:
            data_items.append(OutputData(
                [start_time], [FLAG_UNDEFINED], [FLAG_END]
            ))

        if data_tail.flags.size and data_tail.flags[0] != FLAG_START:
            data_items.append(OutputData(
                [end_time + SAMPLING], [data_removed.odirs[-1]], [FLAG_START]
            ))

        data_items.append(data_tail)

        self._data = OutputData(*join_data(data_items))

    def _reset_table(self):
        """ Reset the orbit direction table. """
        self._products = Products([], [], [])
        self._data = OutputData(
            empty(0, 'datetime64[ms]'), empty(0, 'int8'), empty(0, 'int8')
        )
        self._product_set = set()
        self._changed = True

    def _load_table(self, cdf):
        """ Load orbit direction table from a CDF file. """

        def _parse_time_range(value):
            start, end = [datetime64(v, 'ms') for v in value.split('/')]
            return start, end

        times = CdfTypeEpoch.decode(cdf.raw_var("Timestamp")[...])
        odirs = cdf["OrbitDirection"][...]
        flags = cdf["BoundaryType"][...]

        products = list(cdf.attrs['SOURCES'])
        time_ranges = [
            _parse_time_range(str_)
            for str_ in cdf.attrs['SOURCE_TIME_RANGES']
        ]

        start_times = [start_time for start_time, _ in time_ranges]
        end_times = [end_time for _, end_time in time_ranges]

        self._products = Products(products, start_times, end_times)
        self._data = OutputData(times, odirs, flags)
        self._product_set = set(products)
        self._changed = False


    def _save_table(self, cdf):
        """ Save orbit direction table to a CDF file. """

        def _set_variable(cdf, variable, data, attrs):
            cdf_type, data_convertor = _TYPE_MAP[data.dtype]
            cdf.new(
                variable, data_convertor.encode(data),
                cdf_type, dims=data.shape[1:],
                #compress=GZIP_COMPRESSION,
                #compress_param=GZIP_COMPRESSION_LEVEL1,
            )
            cdf[variable].attrs.update(attrs)

        cdf.attrs["TITLE"] = self._get_product_id(self._filename)
        cdf.attrs["PRODUCT_DESCRIPTION"] = self.DESCRIPTION or ""
        cdf.attrs["SOURCES"] = self._products.names
        cdf.attrs["SOURCE_TIME_RANGES"] = [
            "%sZ/%sZ" % item
            for item in zip(self._products.start_times, self._products.end_times)
        ]

        _set_variable(cdf, "Timestamp", self._data.times, {
            "DESCRIPTION": "Time stamp",
            "UNITS": "-",
        })

        _set_variable(cdf, "BoundaryType", self._data.flags, {
            "DESCRIPTION": (
                "Boundary type (regular %s, block start %s, block end %s)" % (
                    FLAG_MIDDLE, FLAG_START, FLAG_END
                )
            ),
            "UNITS": "-",
        })

        _set_variable(cdf, "OrbitDirection", self._data.odirs, {
            "UNITS": "-",
            "DESCRIPTION": (
                "Orbit direction after this point. "
                "(ascending %s, descending %s, undefined %s)" % (
                    FLAG_ASCENDING, FLAG_DESCENDING, FLAG_UNDEFINED
                )
            )
        })


class GeoOrbitDirectionTable(OrbitDirectionTable):
    """ Geographic orbit direction lookup table class. """
    DESCRIPTION = "Orbit directions boundaries in geographic coordinates."


class QDOrbitDirectionTable(OrbitDirectionTable):
    """ Quasi-dipole orbit direction lookup table class """
    DESCRIPTION = "Orbit directions boundaries in quasi-dipole coordinates."


def process_variable(times, values, has_product_before, has_product_after):
    """ process single variable. """

    def _reformat(extrema_times, ascending_pass):
        return OutputData(
            extrema_times,
            FLAGS_ORBIT_DIRECTION[ascending_pass.astype('int')],
            full(extrema_times.shape, FLAG_MIDDLE, 'int8'),
        )

    result = []

    if not has_product_before:
        # start
        result.append(OutputData(
            [times[0]], FLAGS_ORBIT_DIRECTION[[int(values[1] >= values[0])]],
            [FLAG_START]
        ))
        # unfiltered head
        result.append(_reformat(*find_inversion_points(times[:3], values[:3])))

    result.append(_reformat(
        *find_inversion_points(*low_pass_filter(times, values))
    ))

    if not has_product_after:
        # unfiltered tail
        result.append(_reformat(*find_inversion_points(times[-3:], values[-3:])))
        # termination
        result.append(OutputData(
            [times[-1] + SAMPLING], [FLAG_UNDEFINED], [FLAG_END]
        ))

    return OutputData(*join_data(result))


def check_input_data_integrity(data, start_time, end_time):
    time = data[0]
    if time[0] != start_time:
        raise ValueError(
            "Unexpected data start time %s, expected %s!" % (time[0], start_time)
        )
    if time[-1] != end_time:
        raise ValueError(
            "Unexpected data end time %s, expected %s!" % (time[-1], end_time)
        )

    dtime = time[1:] - time[:-1]
    if dtime.max() > SAMPLING or dtime.min() < SAMPLING:
        raise ValueError(
            "Non-equal sampling from %s to %s!" %(dtime.min(), dtime.max())
        )


def get_times_and_latitudes(times, lats, lons, rads): # pylint: disable=unused-argument
    """ Get geographic latitudes for the given input parameters. """
    return times, lats


def get_times_and_qd_latitudes(times, lats, lons, rads):
    """ Get quasi-dipole latitudes for the given input parameters. """
    qd_lats, _ = eval_qdlatlon(
        lats, lons, rads*1e-3,
        mjd2000_to_decimal_year(datetime64_to_mjd2000(times))
    )
    return times, qd_lats


def datetime64_to_mjd2000(times):
    """ Convert datetime64 array to MJD2000. """
    return MS2DAYS*(
        asarray(times, 'M8[ms]') - datetime64('2000')
    ).astype('float64')


def low_pass_filter(times, values):
    """ Simple smoothing filter. Note that the low-pass filter trims the data
    by one element from each side.
    """
    new_times = times[1:-1]
    new_values = values[1:-1].copy()
    new_values += values[2:]
    new_values += values[:-2]
    new_values *= 1.0/3.0
    return new_times, new_values


def find_inversion_points(times, lats):
    """ Find points of max/min. latitudes were the orbit direction gets
    inverted.
    """
    index = lookup_extrema(lats)
    ascending_pass = lats[index] < 0
    extrema_times = find_extrema(
        times.astype('float64'), lats, index
    ).astype(times.dtype)
    return extrema_times, ascending_pass


def lookup_extrema(values):
    """ Find indices of local extrema of the array values. """
    non_descending = values[1:] - values[:-1] >= 0
    return 1 + (non_descending[1:] != non_descending[:-1]).nonzero()[0]


def find_extrema(x, y, idx):
    """ Find approximate location of the extreme values. """
    #pylint: disable=invalid-name
    idx0, idx1, idx2 = idx - 1, idx, idx + 1
    x0 = x[idx0]
    a1 = x[idx1] - x0
    a2 = x[idx2] - x0
    y0 = y[idx0]
    b1 = y[idx1] - y0
    b2 = y[idx2] - y0
    a1b2, a2b1 = a1*b2, a2*b1
    return x0 + 0.5*(a1*a1b2 - a2*a2b1)/(a1b2 - a2b1)


def slice_data(data, slice_=Ellipsis):
    """ Slice data items. """
    return tuple(data_item[slice_] for data_item in data)


def join_data(data_items):
    """ Concatenate data items. """
    return _join_data(data_items, concatenate)


def join_lists(list_items):
    """ Concatenate tuple of lists. """
    return _join_data(list_items, lambda l: list(chain.from_iterable(l)))


def _join_data(data_items, join_func):
    if not data_items:
        return ()
    accm = tuple([] for _ in data_items[0])
    for data_item in data_items:
        for idx, array_ in enumerate(data_item):
            accm[idx].append(array_)
    return tuple(join_func(list_item) for list_item in accm)


def load_data_from_product(filename, slice_=Ellipsis):
    """ Load data concatenated from a single product. """
    with cdf_open(filename) as cdf:
        times = CdfTypeEpoch.decode(cdf.raw_var("Timestamp")[slice_])
        lats = cdf["Latitude"][slice_]
        lons = cdf["Longitude"][slice_]
        rads = cdf["Radius"][slice_]
    return InputData(times, lats, lons, rads)


def sorted_range(data, start, end, left_closed=True, right_closed=True,
                 margin=0):
    """ Get a slice of a sorted data array matched by the given interval. """
    idx_start, idx_end = None, None

    if start is not None:
        idx_start = searchsorted(data, start, 'left' if left_closed else 'right')
        if margin > 0:
            idx_start = max(0, idx_start - margin)

    if end is not None:
        idx_end = searchsorted(data, end, 'right' if right_closed else 'left')
        if margin > 0:
            idx_end += margin

    return slice(idx_start, idx_end)


class CdfTypeDummy(object):
    """ CDF dummy type conversions. """

    @staticmethod
    def decode(values):
        """ Pass trough and do nothing. """
        return values

    @staticmethod
    def encode(values):
        """ Pass trough and do nothing. """
        return values


class CdfTypeEpoch(object):
    """ CDF Epoch Time type conversions. """
    CDF_EPOCH_1970 = 62167219200000.0

    @classmethod
    def decode(cls, cdf_raw_time):
        """ Convert CDF raw time to datetime64[ms]. """
        return asarray(
            cdf_raw_time - cls.CDF_EPOCH_1970
        ).astype('datetime64[ms]')

    @classmethod
    def encode(cls, time):
        """ Convert datetime64[ms] to CDF raw time. """
        time = asarray(time, 'datetime64[ms]').astype('int64')
        return time + cls.CDF_EPOCH_1970


_TYPE_MAP = {
    dtype("int8"): (CDF_INT1_TYPE, CdfTypeDummy),
    dtype("datetime64[ms]"): (CDF_EPOCH_TYPE, CdfTypeEpoch),
}
