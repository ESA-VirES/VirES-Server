#-------------------------------------------------------------------------------
#
# Leap seconds table
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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

from collections import namedtuple
from datetime import datetime
from numpy import array, searchsorted
from .data import CDF_LEAP_SECONDS


TD_MJD_EPOCH = datetime(1858, 11, 17)
TD_MJD2000_EPOCH = datetime(2000, 1, 1)
MJD2000_TO_MJD_OFFSET = (TD_MJD2000_EPOCH - TD_MJD_EPOCH).days
SECONDS_PER_DAY = 24 * 60 * 60
NANOSECONDS_PER_SECOND = 1000000000
NANOSECONDS_PER_DAY = NANOSECONDS_PER_SECOND * SECONDS_PER_DAY
INT64_MIN = -9223372036854775808


class LeapSecondsTableParsingError(Exception):
    """ Lookup table parsing error. """


class LeapNanoSecondsTable:
    """ Leap "seconds" table calculating offset between TAI and UTC timelines
    in nanoseconds.

    NOTE: To be compliant with other CDF libraries, the time drift between
    1960-01-01 and 1972-01-01 is calculated from integer Modified Julian Date.
    The drift is stepwise daily constant function.

    There are occasional +1ns deviations from other implementations
    in the calculated drift between 1960-01-01 and 1972-01-01.
    These are caused by uncompensated FP round-off errors in the other
    implementations. Our calculation uses exact integer arithmetic operations.
    """

    @classmethod
    def load_from_file(cls, filename):
        """ Load leap-seconds data from file. """
        with open(filename, encoding="ascii") as file:
            return cls(file)

    def __init__(self, source):

        records = list(
            self._expand_drift_offset_records(
                self._convert_cdf_leap_seconds_records(
                    _parse_cdf_leap_seconds(source)
                )
            )
        )

        self.times_utc = array([record.utc for record in records], "int64")
        self.offsets_tai2utc = array([record.offset for record in records], "int64")
        self.times_tai = self.times_utc + self.offsets_tai2utc

        self._get_tai2utc_offset_from_utc = LookupTable(self.times_utc, self.offsets_tai2utc)
        self._get_tai2utc_offset_from_tai = LookupTable(self.times_tai, self.offsets_tai2utc)

    def get_tai_offset_for_utc2000ns(self, utc2000ns):
        """ Covert UTC2000 nanoseconds to TT2000 nanoseconds. """
        return self._get_tai2utc_offset_from_utc(utc2000ns)

    def get_tai_offset_for_tai2000ns(self, tai2000ns):
        """ Covert TT2000 nanoseconds to UTC2000 nanoseconds. """
        return self._get_tai2utc_offset_from_tai(tai2000ns)

    @staticmethod
    def _expand_drift_offset_records(offset_records):
        offset_records = list(offset_records)

        OffsetRecord = namedtuple("OffsetRecord", ["utc", "offset"])

        record_pairs = (
            (offset_records[idx], offset_records[idx+1])
            for idx in range(len(offset_records) - 1)
        )

        for record, next_record in record_pairs:
            if record.drift_slope == 0:
                yield OffsetRecord(record.utc, record.offset)
            else:
                # expand the daily drift updates (1960-01-01/1972-01-01)
                for utc in range(record.utc, next_record.utc, NANOSECONDS_PER_DAY):
                    offset = record.offset + record.drift_slope * (
                        1 + 2 * (
                            (utc - record.drift_offset) // NANOSECONDS_PER_DAY
                        )
                    )
                    yield OffsetRecord(utc, offset)

        last_record = offset_records[-1]
        if last_record.drift_slope != 0:
            raise ValueError(
                "Unbound leap seconds drift period. "
                "Cannot build the lookup table."
            )
        yield OffsetRecord(last_record.utc, last_record.offset)

    @classmethod
    def _convert_cdf_leap_seconds_records(cls, cdf_leap_seconds_records):
        """ Convert the leap seconds information to more appropriate values
        to simplify the later conversions.
        """
        def _mjd_to_utc2000ns(mjd):
            return (mjd - MJD2000_TO_MJD_OFFSET) * NANOSECONDS_PER_DAY

        OffsetRecord = namedtuple(
            "OffsetRecord",
            ["utc", "offset", "drift_offset", "drift_slope"]
        )

        # look-up table lower bound
        yield OffsetRecord(INT64_MIN, 0, 0, 0)

        for record in cdf_leap_seconds_records:
            # UTC2000 - UTC nanoseconds from UTC 2000-01-01T00:00:00
            utc2000ns = _mjd_to_utc2000ns(record.mjd)

            # offset in nanoseconds from TT20000 to UTC2000
            offset = int(round(NANOSECONDS_PER_SECOND * record.tai_offset))

            if record.drift_slope == 0.0:
                drift_offset, drift_slope = 0, 0

            else:
                # drift offset - UTC2000 nanoseconds
                drift_offset = _mjd_to_utc2000ns(record.drift_mjd_offset)

                # drift offset - nanoseconds per half-day
                drift_slope = int(round(
                    (NANOSECONDS_PER_SECOND // 2) * record.drift_slope
                ))

            yield OffsetRecord(utc2000ns, offset, drift_offset, drift_slope)


def _parse_cdf_leap_seconds(source, comment_delimiter=";"):
    """ Parse CDF peap seconds table. """

    def _date_to_mjd(year, month, day):
        """ Convert datetime.datetime object to integer Modified Julian Date """
        return (datetime(year, month, day) - TD_MJD_EPOCH).days

    CDFLeapSecodsRecord = namedtuple(
        "CDFLeapSecodsRecord",
        ["mjd", "tai_offset", "drift_mjd_offset", "drift_slope"]
    )

    line_no = 0
    try:
        for line_no, line in enumerate(source, 1):
            line = line.partition(comment_delimiter)[0].strip()
            if not line:
                continue
            (
                year, month, day, tai_offset, drift_mjd_offset, drift_slope,
            ) = line.split()

            drift_mjd_offset = float(drift_mjd_offset)
            if drift_mjd_offset != int(drift_mjd_offset):
                raise ValueError("Drift offset is expected to be an integer MJD!")

            yield CDFLeapSecodsRecord(
                _date_to_mjd(int(year), int(month), int(day)),
                float(tai_offset),
                int(drift_mjd_offset),
                float(drift_slope),
            )
    except ValueError as error:
        raise LeapSecondsTableParsingError(
            f"Failed to parse the Leap seconds table! {line_no} {error}"
        ) from error


class LookupTable:
    """ Lookup table for a stepwise constant function.

        For N breakpoints x_i, and N values y_i, and x >= x_0:
            x_i <= x < x_(i+1) --> y_i
            x_(N-1) <= x       --> y_(N-1)

        Values x <= x_0 are not allowed.
    """
    #pylint: disable=invalid-name,too-few-public-methods

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __call__(self, x):
        idx = searchsorted(self.x, x, side="right") - 1
        return self.y[idx]


LEAP_NANOSECONDS_TABLE = LeapNanoSecondsTable.load_from_file(CDF_LEAP_SECONDS)
