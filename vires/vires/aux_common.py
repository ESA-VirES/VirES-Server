#-------------------------------------------------------------------------------
#
# common auxiliary file handling code
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
# pylint: disable=unused-argument,too-few-public-methods

from os.path import exists
from numpy import array, full, nan
from .cdf_util import (
    cdf_open, cdf_time_subset, cdf_time_interp,
    CDF_EPOCH_TYPE, datetime_to_cdf_rawtime, cdf_rawtime_to_datetime,
)
from .time_util import datetime_to_mjd2000, mjd2000_to_datetime, timedelta


def render_filename(format_, start, end, **kwargs):
    """ Render filename from a format string with a time formatting. """
    def _format_time(dt_):
        return (dt_ + timedelta(microseconds=500000)).strftime("%Y%m%dT%H%M%S")
    return format_.format(
        start=_format_time(start), end=_format_time(end), **kwargs
    )


class BaseReader(object):
    """ Base reader class. """
    TIME_FIELD = None
    DATA_FIELDS = None
    TYPES = {}
    NODATA = {}
    SUBSTET_PARAMETERS = {"margin": 1}
    INTERPOLATION_KIND = None

    def __init__(self, filename, product_set=None):
        self._filename = filename
        self.product_set = set() if product_set is None else product_set

    def _update_product_set(self, cdf, start, end):
        """ Update product set by entering product matched by the interval. """
        raise NotImplementedError

    @staticmethod
    def _from_datetime(time):
        """ Convert time from datetime """
        raise NotImplementedError

    @staticmethod
    def _to_datetime(time):
        """ Convert time to datetime """
        raise NotImplementedError

    @classmethod
    def get_nodata(cls, nodata=None):
        """ Get the no-data filled with the defaults. """
        full_nodata = cls.NODATA.copy()
        if nodata:
            full_nodata.update(nodata)
        return full_nodata

    def subset(self, start, stop, fields=None):
        """ Extract data subset matched by the time interval. """
        fields = (self.TIME_FIELD,) + self.DATA_FIELDS if fields is None else fields

        if not exists(self._filename):
            types = self.TYPES
            return {field: array([], types.get(field)) for field in fields}

        start = self._from_datetime(start)
        stop = self._from_datetime(stop)

        with cdf_open(self._filename) as cdf:
            result = dict(cdf_time_subset(
                cdf, start, stop, fields=fields, time_field=self.TIME_FIELD,
                **self.SUBSTET_PARAMETERS
            ))
            self._update_product_set(cdf, start, stop)

        return result

    def interpolate(self, time, nodata=None, fields=None, kind=None):
        """ Interpolate data at given times. """
        fields = self.DATA_FIELDS if fields is None else fields
        nodata = self.get_nodata(nodata)

        if not exists(self._filename):
            types = self.TYPES
            return {
                field: full(time.shape, nodata.get(field, nan), types.get(field))
                for field in fields
            }

        with cdf_open(self._filename) as cdf:
            bounds = (time.min(), time.max()) if time.size > 0 else None
            result = dict(cdf_time_interp(
                cdf, time, fields, nodata=nodata, time_field=self.TIME_FIELD,
                kind=(kind or self.INTERPOLATION_KIND), types=self.TYPES,
                bounds=bounds
            ))
            if bounds:
                self._update_product_set(cdf, *bounds)

        return result


class NoSourceMixIn(object):
    """ No source mix-in class """
    def _update_product_set(self, cdf, start, end):
        pass


class SingleSourceMixIn(object):
    """ Single source mix-in class """
    def _update_product_set(self, cdf, start, end):
        validity_start, validity_end = cdf.attrs['VALIDITY']
        if validity_start <= end and validity_end >= start:
            self.product_set.add(cdf.attrs['SOURCE'])


class MJD2000TimeMixIn(object):
    """ MJD2000 mix-in class. """
    @staticmethod
    def _from_datetime(time):
        return datetime_to_mjd2000(time)

    @staticmethod
    def _to_datetime(time):
        return mjd2000_to_datetime(time)


class CdfEpochTimeMixIn(object):
    """ CDF_EPOCH mix-in class. """
    @staticmethod
    def _from_datetime(time):
        return datetime_to_cdf_rawtime(time, CDF_EPOCH_TYPE)

    @staticmethod
    def _to_datetime(time):
        return cdf_rawtime_to_datetime(time, CDF_EPOCH_TYPE)
