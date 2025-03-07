#-------------------------------------------------------------------------------
#
# Products metadata extraction -
# CDF metadata reader for datasets with annotated time-span attribute.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

import re
from datetime import datetime, timedelta
from vires.time_util import naive_to_utc
from .base import CDFMetadataReader

MAX_SUBSECOND = timedelta(seconds=1) - timedelta(microseconds=1)


class TimeSpanCdfMetadataReader(CDFMetadataReader):
    """ Metadata reader for CDF files with annotated time-span as global
    CDF attribute.
    """
    TYPE = "CDF-with-timespan-attribute"
    DEFAULT_TIMESPAN_ATTRIBUTE = "Timespan"
    RE_TIMESTAMP = re.compile(
        r'^UTC=(?P<year>\d{4,4})-(?P<month>\d{2,2})-(?P<day>\d{2,2})T'
        r'(?P<hour>\d{2,2}):(?P<minute>\d{2,2}):(?P<second>\d{2,2})$'
    )

    @classmethod
    def extract_options(cls, product_type):
        """ Extract optional non-default timespan attribute name. """
        return {
            "attribute_name": product_type.definition.get(
                "timespanAttributeName", cls.DEFAULT_TIMESPAN_ATTRIBUTE
            )
        }

    @classmethod
    def read_cdf_metadata(cls, cdf, **options):
        begin_time, end_time = cls._read_timespan_attribute(
            cdf, attribute_name=options["attribute_name"]
        )
        return {
            "format": cls.TYPE,
            "begin_time": begin_time,
            "end_time": end_time,
        }

    @classmethod
    def _read_timespan_attribute(cls, cdf, attribute_name):

        try:
            start, end = cdf.attrs[attribute_name]
        except (KeyError, ValueError, TypeError):
            raise ValueError(
                f"Failed to read the {attribute_name} global attribute!"
            ) from None

        return (
            cls._parse_utc_timestamp(start),
            cls._parse_utc_timestamp(end) + MAX_SUBSECOND,
        )

    @classmethod
    def _parse_utc_timestamp(cls, value):
        if not (match := cls.RE_TIMESTAMP.match(value)):
            raise ValueError(f"Invalid timestamp value {value}!")
        return naive_to_utc(datetime(**{
            key: int(value) for key, value in match.groupdict().items()
        }))
