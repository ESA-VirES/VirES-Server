#-------------------------------------------------------------------------------
#
# Orbit direction - update of the lookup tables
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
# pylint: disable=relative-beyond-top-level,missing-module-docstring

from os import remove, rename
from os.path import exists, basename, splitext
from logging import getLogger
from bisect import bisect_left, bisect_right
from numpy import asarray, empty
from ..cdf_util import cdf_open, CDF_EPOCH_TYPE
from ..cdf_data_reader import read_cdf_data
from ..cdf_write_util import cdf_add_variable, CdfTypeEpoch
from ..exceptions import DataIntegrityError
from .common import (
    FLAG_START, FLAG_MIDDLE, FLAG_END,
    FLAG_ASCENDING, FLAG_DESCENDING, FLAG_UNDEFINED,
)
from .util import Products, OutputData


class OrbitDirectionTable():
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
        except: # pylint: disable=try-except-raise
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

    def update(self, data, product_id, start_time, end_time,
               margin_before, margin_after):
        """ Update orbit direction table file. """
        self._merge_data(data, start_time, end_time, margin_before, margin_after)
        self._insert_product(product_id, start_time, end_time)
        self._changed = True

    def dump(self):
        """ Dump content of the orbit direction table. """
        self._data.dump()

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
        self._products = Products.join(
            self._products[:idx],
            self._products[idx+1:],
        )
        self._product_set.remove(product_id)
        return start_time, end_time

    def _insert_product(self, product_id, start_time, end_time):
        idx_start = bisect_left(self._products.end_times, start_time)
        idx_end = bisect_right(self._products.start_times, end_time)
        self._products = Products.join(
            self._products[:idx_start],
            Products([product_id], [start_time], [end_time]),
            self._products[idx_end:],
        )
        self._product_set.add(product_id)

    @staticmethod
    def _get_product_id(filename):
        return splitext(basename(filename))[0]

    def _merge_data(self, data, start_time, end_time,
                    margin_before, margin_after):
        start_trim_time = start_time - margin_before
        end_trim_time = end_time + margin_after

        head = self._data.time_subset(end=start_trim_time, right_closed=False)
        body = data.time_subset(start=start_trim_time, end=end_trim_time)
        tail = self._data.time_subset(start=end_trim_time, left_closed=False)

        if (
                not head.is_empty and head.flags[-1] != FLAG_END and
                not body.is_empty and body.flags[0] == FLAG_START
            ):
            raise DataIntegrityError("Unexpected segment start.")

        if (
                not tail.is_empty and tail.flags[0] != FLAG_START and
                not body.is_empty and body.flags[-1] == FLAG_END
            ):
            raise DataIntegrityError("Unexpected segment end.")

        self._data = OutputData.join(head, body, tail)

    def _cut_out_data(self, start_time, end_time):
        """" Remove data within the given time interval. """
        head = self._data.time_subset(end=start_time, right_closed=False)
        removed = self._data.time_subset(start=start_time, end=end_time)
        tail = self._data.time_subset(start=end_time, right_closed=False)

        data_items = [head]

        if not head.is_empty and head.flags[-1] != FLAG_END:
            data_items.append(OutputData.get_end(start_time))

        if not tail.is_empty and tail.flags[0] != FLAG_START:
            data_items.append(OutputData.get_start(end_time, removed.odirs[-1]))

        data_items.append(tail)

        self._data = OutputData.join(*data_items)

    def _reset_table(self):
        """ Reset the orbit direction table. """
        self._products = Products()
        self._data = OutputData()
        self._product_set = set()
        self._changed = True

    def _load_table(self, cdf):
        """ Load orbit direction table from a CDF file. """

        def _read_time_ranges(attr):
            attr._raw = True # pylint: disable=protected-access
            data = asarray([CdfTypeEpoch.decode(item) for item in attr])
            if data.size == 0:
                return empty(0, 'float64'), empty(0, 'float64')
            return data[:, 0], data[:, 1]

        products = list(cdf.attrs['SOURCES'])
        start_times, end_times = _read_time_ranges(
            cdf.attrs['SOURCE_TIME_RANGES']
        )
        self._products = Products(products, start_times, end_times)
        self._product_set = set(products)

        dataset = read_cdf_data(
            cdf, ["Timestamp", "OrbitDirection", "BoundaryType"]
        )
        self._data = OutputData(
            dataset["Timestamp"],
            dataset["OrbitDirection"],
            dataset["BoundaryType"],
        )

        self._changed = False

    def _save_table(self, cdf):
        """ Save orbit direction table to a CDF file. """

        def _write_time_ranges(attr, start_times, end_times):
            for idx, item in enumerate(zip(start_times, end_times)):
                attr.new(
                    data=CdfTypeEpoch.encode(item),
                    type=CDF_EPOCH_TYPE,
                    number=idx,
                )

        cdf.attrs["TITLE"] = self._get_product_id(self._filename)
        cdf.attrs["PRODUCT_DESCRIPTION"] = self.DESCRIPTION or ""
        cdf.attrs["SOURCES"] = self._products.names
        cdf.attrs.new("SOURCE_TIME_RANGES")
        _write_time_ranges(
            cdf.attrs["SOURCE_TIME_RANGES"],
            self._products.start_times,
            self._products.end_times
        )
        cdf.attrs['NEIGHBOUR_DISTANCE'] = 1000.
        cdf.attrs['NEIGHBOUR_OVERLAP'] = 3000.

        cdf_add_variable(cdf, "Timestamp", self._data.times, {
            "DESCRIPTION": "Time stamp",
            "UNITS": "-",
        })

        cdf_add_variable(cdf, "BoundaryType", self._data.flags, {
            "DESCRIPTION": (
                "Boundary type (regular %s, block start %s, block end %s)" % (
                    FLAG_MIDDLE, FLAG_START, FLAG_END
                )
            ),
            "UNITS": "-",
        })

        cdf_add_variable(cdf, "OrbitDirection", self._data.odirs, {
            "UNITS": "-",
            "DESCRIPTION": (
                "Orbit direction after this point. "
                "(ascending %s, descending %s, undefined %s)" % (
                    FLAG_ASCENDING, FLAG_DESCENDING, FLAG_UNDEFINED
                )
            )
        })
