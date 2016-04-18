#-------------------------------------------------------------------------------
#
# Testing Time Utilities
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=missing-docstring

from math import floor
from calendar import timegm
import unittest
from datetime import datetime
from vires.time_util import (
    DT_1970, is_leap_year, days_per_year, time_to_seconds,
    time_to_day_fraction, day_fraction_to_time,
    day2k_to_date, date_to_day2k, day2k_to_year, year_to_day2k,
    datetime_to_mjd2000, mjd2000_to_datetime,
    datetime_to_unix_epoch, unix_epoch_to_datetime,
    unix_epoch_to_mjd2000, mjd2000_to_unix_epoch,
    datetime_to_decimal_year, decimal_year_to_datetime,
    mjd2000_to_decimal_year, decimal_year_to_mjd2000,
    datetime_mean,
)

class TestTimeUtils(unittest.TestCase):

    def test_datetime_mean(self):
        self.assertEqual(
            datetime_mean(datetime(2016, 3, 10), datetime(2016, 3, 11)),
            datetime(2016, 3, 10, 12, 0)
        )

    def test_mjd2000_to_decimal_year(self):
        test_values = [
            (
                datetime_to_mjd2000(dt_obj),
                datetime_to_decimal_year(dt_obj)
            ) for dt_obj in [
                datetime(2000, 1, 1, 0, 0, 0, 0),
                datetime(2100, 1, 1, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 0, 0, 0),
                datetime(2016, 3, 30, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 59, 59, 0),
                datetime(2016, 3, 30, 23, 59, 59, 999000),
                datetime(2016, 3, 30, 23, 59, 59, 999999),
                datetime(1582, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        for mjd2000, result in test_values:
            try:
                self.assertAlmostEqual(
                    mjd2000_to_decimal_year(mjd2000), result, delta=1e-15
                )
            except:
                print "Failed: ", (mjd2000, result)
                raise

    def test_decimal_year_to_mjd2000(self):
        test_values = [
            (
                datetime_to_decimal_year(dt_obj),
                datetime_to_mjd2000(dt_obj)
            ) for dt_obj in [
                datetime(2000, 1, 1, 0, 0, 0, 0),
                datetime(2100, 1, 1, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 0, 0, 0),
                datetime(2016, 3, 30, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 59, 59, 0),
                datetime(2016, 3, 30, 23, 59, 59, 999000),
                datetime(2016, 3, 30, 23, 59, 59, 999999),
                datetime(1582, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        for dec_year, result in test_values:
            try:
                self.assertAlmostEqual(
                    decimal_year_to_mjd2000(dec_year), result, delta=5e-11
                )
            except:
                print "Failed: ", (dec_year, result)
                raise

    def test_decimal_year_to_datetime(self):
        # NOTE: Gregorian calender only.
        # Year 1582 is not correct because of the 10 days gap.
        test_values = [
            (
                year + (
                    datetime(year, month, day, hour, min_, sec, usec) -
                    datetime(year, 1, 1)
                ).total_seconds() / (
                    datetime(year + 1, 1, 1) - datetime(year, 1, 1)
                ).total_seconds(),
                datetime(year, month, day, hour, min_, sec, usec)
            ) for year, month, day, hour, min_, sec, usec
            in [
                (2000, 1, 1, 0, 0, 0, 0),
                (2100, 1, 1, 23, 59, 0, 0),
                (2016, 3, 30, 23, 0, 0, 0),
                (2016, 3, 30, 23, 59, 0, 0),
                (2016, 3, 30, 23, 59, 59, 0),
                (2016, 3, 30, 23, 59, 59, 999000),
                (2016, 3, 30, 23, 59, 59, 999999),
                #(1582, 10, 15, 0, 0, 0, 1000),
                (1583, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        self.assertEqual(
            decimal_year_to_datetime(2016.0), datetime(2016, 1, 1, 0, 0, 0, 0)
        )
        for dec_year, result in test_values:
            try:
                self.assertAlmostEqual(
                    (decimal_year_to_datetime(dec_year)- result).total_seconds(),
                    0.0, delta=5e-6 # assuming 10 usec precision
                )
                self.assertAlmostEqual(
                    datetime_to_decimal_year(decimal_year_to_datetime(dec_year)),
                    dec_year, delta=5e-14
                )
            except:
                print "Failed: ", (dec_year, result)
                raise

    def test_datetime_to_decimal_year(self):
        # NOTE: Gregorian calender only.
        test_values = [
            (
                datetime(year, month, day, hour, min_, sec, usec),
                year + (
                    datetime(year, month, day, hour, min_, sec, usec) -
                    datetime(year, 1, 1)
                ).total_seconds() / (
                    datetime(year + 1, 1, 1) - datetime(year, 1, 1)
                ).total_seconds(),
            ) for year, month, day, hour, min_, sec, usec
            in [
                (2000, 1, 1, 0, 0, 0, 0),
                (2100, 1, 1, 23, 59, 0, 0),
                (2016, 3, 30, 23, 0, 0, 0),
                (2016, 3, 30, 23, 59, 0, 0),
                (2016, 3, 30, 23, 59, 59, 0),
                (2016, 3, 30, 23, 59, 59, 999000),
                (2016, 3, 30, 23, 59, 59, 999999),
                #(1582, 10, 15, 0, 0, 0, 1000),
                (1583, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        self.assertEqual(
            datetime(2016, 1, 1, 0, 0, 0, 0), decimal_year_to_datetime(2016.0)
        )
        for dt_obj, result in test_values:
            try:
                self.assertAlmostEqual(
                    datetime_to_decimal_year(dt_obj), result, delta=5e-14
                )
                self.assertAlmostEqual(
                    (
                        decimal_year_to_datetime(datetime_to_decimal_year(dt_obj)) -
                        dt_obj
                    ).total_seconds(), 0.0,
                    delta=5e-6 # assuming 10 usec precision
                )
            except:
                print "Failed: ", (dt_obj, result)
                raise

    def test_mjd2000_to_unix_epoch(self):
        test_values = [
            (
                datetime_to_mjd2000(dt_obj),
                datetime_to_unix_epoch(dt_obj)
            ) for dt_obj in [
                datetime(2000, 1, 1, 0, 0, 0, 0),
                datetime(2100, 1, 1, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 0, 0, 0),
                datetime(2016, 3, 30, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 59, 59, 0),
                datetime(2016, 3, 30, 23, 59, 59, 999000),
                datetime(2016, 3, 30, 23, 59, 59, 999999),
                datetime(1582, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        for mjd2000, result in test_values:
            try:
                self.assertAlmostEqual(
                    mjd2000_to_unix_epoch(mjd2000), result, delta=5e-6
                )
            except:
                print "Failed: ", (mjd2000, result)
                raise

    def test_unix_epoch_to_mjd2000(self):
        test_values = [
            (
                datetime_to_unix_epoch(dt_obj),
                datetime_to_mjd2000(dt_obj)
            ) for dt_obj in [
                datetime(2000, 1, 1, 0, 0, 0, 0),
                datetime(2100, 1, 1, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 0, 0, 0),
                datetime(2016, 3, 30, 23, 59, 0, 0),
                datetime(2016, 3, 30, 23, 59, 59, 0),
                datetime(2016, 3, 30, 23, 59, 59, 999000),
                datetime(2016, 3, 30, 23, 59, 59, 999999),
                datetime(1582, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        for ux_epoch, result in test_values:
            try:
                self.assertAlmostEqual(
                    unix_epoch_to_mjd2000(ux_epoch), result, delta=5e-11
                )
            except:
                print "Failed: ", (ux_epoch, result)
                raise


    def test_unix_epoch_to_datetime(self):
        # NOTE: Gregorian calender only.
        test_values = [
            (
                (
                    datetime(year, month, day, hour, min_, sec, usec) - DT_1970
                ).total_seconds(),
                datetime(year, month, day, hour, min_, sec, usec)
            ) for year, month, day, hour, min_, sec, usec
            in [
                (2000, 1, 1, 0, 0, 0, 0),
                (2100, 1, 1, 23, 59, 0, 0),
                (2016, 3, 30, 23, 0, 0, 0),
                (2016, 3, 30, 23, 59, 0, 0),
                (2016, 3, 30, 23, 59, 59, 0),
                (2016, 3, 30, 23, 59, 59, 999000),
                (2016, 3, 30, 23, 59, 59, 999999),
                (1582, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        self.assertEqual(
            unix_epoch_to_datetime(0), datetime(1970, 1, 1, 0, 0, 0, 0)
        )
        for ux_epoch, result in test_values:
            try:
                self.assertAlmostEqual(
                    (unix_epoch_to_datetime(ux_epoch)- result).total_seconds(),
                    0.0, delta=5e-6 # assuming 10 usec precision
                )
                self.assertAlmostEqual(
                    datetime_to_unix_epoch(unix_epoch_to_datetime(ux_epoch)),
                    ux_epoch, delta=5e-7
                )
            except:
                print "Failed: ", (ux_epoch, result)
                raise

    def test_datetime_to_unix_epoch(self):
        # NOTE: Gregorian calender only.
        test_values = [
            (
                datetime(year, month, day, hour, min_, sec, usec),
                (
                    datetime(year, month, day, hour, min_, sec, usec) - DT_1970
                ).total_seconds()
            ) for year, month, day, hour, min_, sec, usec
            in [
                (2000, 1, 1, 0, 0, 0, 0),
                (2100, 1, 1, 23, 59, 0, 0),
                (2016, 3, 30, 23, 0, 0, 0),
                (2016, 3, 30, 23, 59, 0, 0),
                (2016, 3, 30, 23, 59, 59, 0),
                (2016, 3, 30, 23, 59, 59, 999000),
                (2016, 3, 30, 23, 59, 59, 999999),
                (1582, 10, 15, 0, 0, 0, 1000),
            ]
        ]
        self.assertEqual(
            datetime_to_unix_epoch(datetime(1970, 1, 1, 0, 0, 0, 0)), 0
        )
        for dt_obj, result in test_values:
            try:
                self.assertAlmostEqual(
                    datetime_to_unix_epoch(dt_obj), result, delta=5e-7
                )
                self.assertAlmostEqual(
                    (
                        unix_epoch_to_datetime(datetime_to_unix_epoch(dt_obj)) -
                        dt_obj
                    ).total_seconds(), 0.0,
                    delta=5e-6 # assuming 10 usec precision
                )
                self.assertEqual(
                    floor(datetime_to_unix_epoch(dt_obj)),
                    timegm(dt_obj.timetuple())
                )
            except:
                print "Failed: ", (dt_obj, result)
                raise

    def test_mjd2000_to_datetime(self):
        test_values = [
            (
                date_to_day2k(year, month, day) +
                time_to_day_fraction(hour, min_, sec, usec),
                datetime(year, month, day, hour, min_, sec, usec)
            ) for year, month, day, hour, min_, sec, usec
            in [
                (2000, 1, 1, 0, 0, 0, 0),
                (2100, 1, 1, 23, 59, 0, 0),
                (2016, 3, 30, 23, 0, 0, 0),
                (2016, 3, 30, 23, 59, 0, 0),
                (2016, 3, 30, 23, 59, 59, 0),
                (2016, 3, 30, 23, 59, 59, 999000),
                (2016, 3, 30, 23, 59, 59, 999999),
                (1582, 10, 15, 0, 0, 0, 1000),
                (1582, 10, 4, 0, 0, 0, 1),
            ]
        ]
        self.assertEqual(
            mjd2000_to_datetime(0), datetime(2000, 1, 1, 0, 0, 0, 0)
        )
        for mjd2000, result in test_values:
            try:
                self.assertAlmostEqual(
                    (mjd2000_to_datetime(mjd2000) - result).total_seconds(),
                    0.0, delta=5e-6 # assuming 10 usec precision
                )
                self.assertAlmostEqual(
                    datetime_to_mjd2000(mjd2000_to_datetime(mjd2000)),
                    mjd2000, delta=5e-11
                )
            except:
                print "Failed: ", (mjd2000, result)
                raise

    def test_datetime_to_mjd2000(self):
        test_values = [
            (
                datetime(year, month, day, hour, min_, sec, usec),
                date_to_day2k(year, month, day) +
                time_to_day_fraction(hour, min_, sec, usec)
            ) for year, month, day, hour, min_, sec, usec
            in [
                (2000, 1, 1, 0, 0, 0, 0),
                (2100, 1, 1, 23, 59, 0, 0),
                (2016, 3, 30, 23, 0, 0, 0),
                (2016, 3, 30, 23, 59, 0, 0),
                (2016, 3, 30, 23, 59, 59, 0),
                (2016, 3, 30, 23, 59, 59, 999000),
                (2016, 3, 30, 23, 59, 59, 999999),
                (1582, 10, 15, 0, 0, 0, 1000),
                (1582, 10, 4, 0, 0, 0, 1),
            ]
        ]
        self.assertEqual(
            datetime_to_mjd2000(datetime(2000, 1, 1, 0, 0, 0, 0)), 0
        )
        for dt_obj, result in test_values:
            try:
                self.assertAlmostEqual(
                    datetime_to_mjd2000(dt_obj), result, delta=1e-15
                )
                self.assertAlmostEqual(
                    (
                        mjd2000_to_datetime(datetime_to_mjd2000(dt_obj)) -
                        dt_obj
                    ).total_seconds(), 0.0,
                    delta=5e-6 # assuming 10 usec precision
                )
            except:
                print "Failed: ", (dt_obj, result)
                raise

    def test_year_to_day2k(self):
        test_values = [
            (year, date_to_day2k(year, 1, 1)) for year in range(1000, 3000)
        ]
        for year, result in test_values:
            try:
                self.assertEqual(year_to_day2k(year), result)
            except:
                print "Failed: ", (year, result)
                raise

    def test_day2k_to_year(self):
        test_values = [
            (date_to_day2k(year, 1, 1), year) for year in range(1000, 3000)
        ] + [
            (date_to_day2k(year, 12, 31), year) for year in range(1000, 3000)
        ]
        for day2k, result in test_values:
            try:
                self.assertEqual(day2k_to_year(day2k), result)
            except:
                print "Failed: ", (day2k, result)
                raise

    def test_date_to_day2k(self):
        test_values = [
            ((2000, 1, 1), 0),
            ((2100, 1, 1), 36525),
            ((2016, 3, 30), 5933),
            ((1582, 10, 15), -152384),
            ((1582, 10, 4), -152385),
        ]
        for date_, result in test_values:
            try:
                self.assertEqual(date_to_day2k(*date_), result)
            except:
                print "Failed: ", (date_, result)
                raise

    def test_day2k_to_date(self):
        test_values = [
            (0, (2000, 1, 1)),
            (36525, (2100, 1, 1)),
            (5933, (2016, 3, 30)),
            (-152384, (1582, 10, 15)),
            (-152385, (1582, 10, 4)),
        ]
        for day2k, result in test_values:
            try:
                self.assertEqual(day2k_to_date(day2k), result)
            except:
                print "Failed: ", (day2k, result)
                raise

    def test_day_fraction_to_time(self):
        test_values = [
            (4.1666666666666664e-02, (1, 0, 0, 0)),
            (1.0 - 4.1666666666666664e-02, (23, 0, 0, 0)),
            (6.9444444444444447e-04, (0, 1, 0, 0)),
            (1.0 - 6.9444444444444447e-04, (23, 59, 0, 0)),
            (1.1574074074074073e-05, (0, 0, 1, 0)),
            (1.0 - 1.1574074074074073e-05, (23, 59, 59, 0)),
            (1.1574074074074074e-11, (0, 0, 0, 1)),
            (1.0 - 1.1574074074074074e-11, (23, 59, 59, 999999)),
            (0.250, (6, 0, 0, 0)), (0.125, (3, 0, 0, 0)),
            (0.250, (6, 0, 0, 0)), (0.375, (9, 0, 0, 0)),
            (0.500, (12, 0, 0, 0)), (0.625, (15, 0, 0, 0)),
            (0.750, (18, 0, 0, 0)), (0.875, (21, 0, 0, 0)),
            (1.000, (24, 0, 0, 0)),
        ]
        for day_fraction, result in test_values:
            try:
                self.assertEqual(
                    day_fraction_to_time(day_fraction), result
                )
            except:
                print "Failed: ", (day_fraction, result)
                raise

    def test_time_to_day_fraction(self):
        test_values = [
            ((1, 0, 0, 0), 4.1666666666666664e-02),
            ((23, 0, 0, 0), 1.0 - 4.1666666666666664e-02),
            ((0, 1, 0, 0), 6.9444444444444447e-04),
            ((23, 59, 0, 0), 1.0 - 6.9444444444444447e-04),
            ((0, 0, 1, 0), 1.1574074074074073e-05),
            ((23, 59, 59, 0), 1.0 - 1.1574074074074073e-05),
            ((0, 0, 0, 1), 1.1574074074074074e-11),
            ((23, 59, 59, 999999), 1.0 - 1.1574074074074074e-11),
            ((6, 0, 0, 0), 0.250),
            ((3, 0, 0, 0), 0.125), ((6, 0, 0, 0), 0.250),
            ((9, 0, 0, 0), 0.375), ((12, 0, 0, 0), 0.500),
            ((15, 0, 0, 0), 0.625), ((18, 0, 0, 0), 0.750),
            ((21, 0, 0, 0), 0.875), ((24, 0, 0, 0), 1.000),
        ]
        for time_, result in test_values:
            try:
                self.assertAlmostEqual(
                    time_to_day_fraction(*time_), result, delta=1e-14
                )
            except:
                print "Failed: ", (time_, result)
                raise

    def test_time_to_seconds(self):
        test_values = [
            ((1, 0, 0, 0), 3600.0),
            ((23, 0, 0, 0), 86400.0 - 3600.0),
            ((0, 1, 0, 0), 60.0),
            ((23, 59, 0, 0), 86400.0 - 60.0),
            ((0, 0, 1, 0), 1.0),
            ((23, 59, 59, 0), 86400.0 - 1.0),
            ((0, 0, 0, 1000), 0.001),
            ((23, 59, 59, 999000), 86400.0 - 0.001),
            ((0, 0, 0, 1), 0.000001),
            ((23, 59, 59, 999999), 86400.0 - 0.000001),
        ]
        for time_, result in test_values:
            try:
                self.assertAlmostEqual(
                    time_to_seconds(*time_), result, delta=1e-9
                )
            except:
                print "Failed: ", (time_, result)
                raise

    def test_days_per_year(self):
        test_values = [
            (1500, 366), (1504, 366), (1505, 365),
            (1900, 365), (1996, 366), (1997, 365),
            (2000, 366), (2002, 365), (2004, 366),
            (2010, 365), (2011, 365), (2012, 366), (2013, 365),
            (2014, 365), (2015, 365), (2016, 366), (2017, 365),
            (2018, 365), (2019, 365), (2020, 366), (2021, 365),
            (2022, 365), (2023, 365), (2024, 366), (2025, 365),
            (2026, 365), (2027, 365), (2028, 366), (2029, 365),
            (2030, 365), (2031, 365), (2032, 366), (2033, 365),
        ]
        for year, result in test_values:
            try:
                self.assertEqual(days_per_year(year), result)
            except:
                print "Failed: ", (year, result)
                raise

    def test_is_leap_year(self):
        test_values = [
            (1500, True), (1504, True), (1505, False),
            (1900, False), (1996, True), (1997, False),
            (2000, True), (2002, False), (2004, True),
            (2010, False), (2011, False), (2012, True), (2013, False),
            (2014, False), (2015, False), (2016, True), (2017, False),
            (2018, False), (2019, False), (2020, True), (2021, False),
            (2022, False), (2023, False), (2024, True), (2025, False),
            (2026, False), (2027, False), (2028, True), (2029, False),
            (2030, False), (2031, False), (2032, True), (2033, False),
        ]
        for year, result in test_values:
            try:
                self.assertEqual(is_leap_year(year), result)
            except:
                print "Failed: ", (year, result)
                raise


if __name__ == "__main__":
    unittest.main()
