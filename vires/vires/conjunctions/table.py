#-------------------------------------------------------------------------------
#
# Conjunction table - update of the lookup tables
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=missing-module-docstring,too-few-public-methods

from logging import getLogger, LoggerAdapter
from os import remove, rename
from os.path import exists, basename, splitext
from numpy import asarray, empty
from ..cdf_util import cdf_open, CDF_EPOCH_TYPE
from ..cdf_data_reader import read_cdf_data
from ..cdf_write_util import cdf_add_variable, CdfTypeEpoch
from ..exceptions import DataIntegrityError
from .extract import extract_conjunctions
from .util import OrderedIntervalsContainer, InputData, OutputData


class ConjunctionsTable():
    """ Low-level conjunction table class """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s conjunctions: %s' % (self.extra["spacecrafts"], msg), kwargs

    def __init__(self, spacecrafts, filename, reset=False, logger=None):
        self._spacecrafts = spacecrafts
        self._filename = filename
        self._products = None
        self._product_set = None
        self._data = None
        self._changed = None
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "spacecrafts": "%s/%s" % spacecrafts,
        })

        if not reset and exists(filename):
            with cdf_open(filename) as cdf:
                self._load_table(cdf)
        else:
            self._reset_table()

    def __contains__(self, product_pair):
        return product_pair in self._product_set

    @property
    def changed(self):
        """ Return true if the table is changed and should be saved. """
        return self._changed

    def save(self):
        """ Save table to a file. """
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
                "saved to %s", self._get_product_id(self._filename)
            )
            self._changed = False
        finally:
            if exists(tmp_filename):
                remove(tmp_filename)

    def remove(self, start_time, end_time):
        """ Remove product from the lookup tables. """
        for removed_pair in self._products.remove(start_time, end_time):
            del self._product_set[removed_pair[2]]
        self._cut_out_data(start_time, end_time)
        self._changed = True
        self.logger.info("%s/%s interval removed", start_time, end_time)

    def update(self, start_time, end_time, orbit1, orbit2, product_pair):
        """ Update table """

        def _convert_input_data(dataset):
            return InputData(
                dataset['Timestamp'], dataset['Latitude'], dataset['Longitude']
            )

        self._merge_data(start_time, end_time, extract_conjunctions(
            _convert_input_data(orbit1),
            _convert_input_data(orbit2),
        ))
        for removed_pair in self._products.insert(*product_pair):
            del self._product_set[removed_pair[2]]
        self._product_set[product_pair[2]] = product_pair[:2]
        self._changed = True
        self.logger.info(
            "%s/%s interval updated from %s",
            start_time, end_time, " ".join(product_pair[2])
        )

    def dump(self):
        """ Dump content of the orbit direction table. """
        self._data.dump()

    def verify(self):
        """ Verify data. """
        self._products.verify()
        if len(self._product_set) != len(self._products):
            raise DataIntegrityError("Non-unique products pairs!")
        self._data.verify()
        self.logger.debug("table verified")

    def _merge_data(self, start_time, end_time, data):
        head = self._data.time_subset(end=start_time, right_closed=False)
        body = data.time_subset(start=start_time, end=end_time)
        tail = self._data.time_subset(start=end_time, left_closed=False)
        self._data = OutputData.join(head, body, tail)

    def _cut_out_data(self, start_time, end_time):
        """" Remove data within the given time interval. """
        head = self._data.time_subset(end=start_time, right_closed=False)
        tail = self._data.time_subset(start=end_time, right_closed=False)
        self._data = OutputData.join(head, tail)

    def _reset_table(self):
        """ Reset the conjunctions table. """
        self._products = OrderedIntervalsContainer()
        self._data = OutputData()
        self._product_set = {}
        self._changed = True
        self.logger.debug("table reset")

    def _load_table(self, cdf):
        """ Load conjunction table from a CDF file. """

        def _read_time_ranges(attr):
            attr._raw = True # pylint: disable=protected-access
            data = asarray([CdfTypeEpoch.decode(item) for item in attr])
            if data.size == 0:
                return empty(0, 'float64'), empty(0, 'float64')
            return data[:, 0], data[:, 1]

        products = [
            tuple(sources.split())
            for sources in cdf.attrs['SOURCES']
        ]
        start_times, end_times = _read_time_ranges(
            cdf.attrs['SOURCE_TIME_RANGES']
        )

        self._products = OrderedIntervalsContainer(
            start_times, end_times, products,
        )
        self._product_set = {
            product_pair: (start, end)
            for start, end, product_pair in self._products
        }

        dataset = read_cdf_data(cdf, ["Timestamp", "AngularSeparation"])
        self._data = OutputData(
            dataset["Timestamp"],
            dataset["AngularSeparation"]
        )

        self._changed = False
        self.logger.debug("table loaded")

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
        cdf.attrs["PRODUCT_DESCRIPTION"] = "%s/%s conjunctions" % self._spacecrafts
        cdf.attrs["SPACECRAFTS"] = self._spacecrafts
        cdf.attrs["SOURCES"] = [
            "%s %s" % (first, second) for first, second in self._products.items
        ]
        cdf.attrs.new("SOURCE_TIME_RANGES")
        _write_time_ranges(
            cdf.attrs["SOURCE_TIME_RANGES"],
            self._products.starts,
            self._products.ends,
        )
        cdf.attrs['NEIGHBOUR_DISTANCE'] = 1000.
        cdf.attrs['NEIGHBOUR_OVERLAP'] = 0.

        cdf_add_variable(cdf, "Timestamp", self._data.times, {
            "DESCRIPTION": "Timestamp",
            "UNITS": "-",
        })

        cdf_add_variable(cdf, "AngularSeparation", self._data.dists, {
            "DESCRIPTION": (
                "Spacecrafts' great-circle distance."
            ),
            "UNITS": "deg",
        })
        self.logger.debug("table saved")

    @staticmethod
    def _get_product_id(filename):
        return splitext(basename(filename))[0]
