#-------------------------------------------------------------------------------
#
# common auxiliary file handling code
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
# pylint: disable=missing-module-docstring
# pylint: disable=too-many-arguments,too-few-public-methods,abstract-method
# pylint: disable=too-many-locals

from os.path import exists
from numpy import array, full, nan, searchsorted
from scipy.interpolate import interp1d
from .cdf_util import (
    cdf_open, get_cdf_data_reader,
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


class BaseReader:
    """ Base data reader class. """
    TIME_FIELD = None
    DATA_FIELDS = None
    TYPES = {}
    NODATA = {}
    SUBSET_PARAMETERS = {"margin": 1}
    INTERPOLATION_KIND = None

    def __init__(self, product_set=None):
        self.product_set = set() if product_set is None else product_set

    @staticmethod
    def _from_datetime(time):
        """ Convert time from datetime """
        raise NotImplementedError

    @staticmethod
    def _to_datetime(time):
        """ Convert time to datetime """
        raise NotImplementedError

    def _subset(self, start, stop, time_field, fields, types, **options):
        """ Extract subset of the data matched by the given time interval. """
        raise NotImplementedError

    def _interpolate(self, time, time_field, fields, types, kind, nodata):
        """ Interpolate data at given times. """
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
        return self._subset(
            start=self._from_datetime(start),
            stop=self._from_datetime(stop),
            time_field=self.TIME_FIELD,
            fields=(
                self.TIME_FIELD,
                *(self.DATA_FIELDS if fields is None else fields)
            ),
            types = self.TYPES,
            **self.SUBSET_PARAMETERS,
        )

    def interpolate(self, time, nodata=None, fields=None, kind=None):
        """ Interpolate data at given times. """

        return self._interpolate(
            time=time,
            time_field=self.TIME_FIELD,
            fields=(self.DATA_FIELDS if fields is None else fields),
            types=self.TYPES,
            kind=(kind or self.INTERPOLATION_KIND),
            nodata=self.get_nodata(nodata),
        )


class CdfReader(BaseReader):
    """ Single CDF file base reader class. """

    def __init__(self, filename, product_set=None):
        super().__init__(product_set=product_set)
        self._filename = filename

    def _subset(self, start, stop, time_field, fields, types, **options):
        def _empty(field):
            return array([], types.get(field))

        if not exists(self._filename):
            return {field: _empty(field) for field in fields}

        with cdf_open(self._filename) as cdf:
            result = subset_time(
                source=get_cdf_data_reader(cdf),
                start=start,
                stop=stop,
                time_field=time_field,
                fields=fields,
                **options
            )
            self.product_set.update(self._get_sources(cdf, start, stop))

        return result

    def _interpolate(self, time, time_field, fields, types, kind, nodata):
        """ Interpolate data at given times. """
        def _no_data(field):
            return full(time.shape, nodata.get(field, nan), types.get(field))

        if not exists(self._filename):
            return {field: _no_data(field) for field in fields}

        with cdf_open(self._filename) as cdf:
            bounds = (time.min(), time.max()) if time.size > 0 else None
            result = interpolate_time(
                source=get_cdf_data_reader(cdf),
                time=time,
                time_field=time_field,
                fields=fields,
                types=types,
                nodata=nodata,
                bounds=bounds,
                kind=kind,
            )
            if bounds:
                self.product_set.update(self._get_sources(cdf, *bounds))

        return result

    def _get_sources(self, cdf, start, end):
        """ Get list of source products matched by the time interval. """
        raise NotImplementedError


class NoSourceMixIn():
    """ No source mix-in class """
    def _get_sources(self, cdf, start, end):
        del cdf, start, end
        return []


class SingleSourceMixIn():
    """ Single source mix-in class """
    def _get_sources(self, cdf, start, end):
        validity_start, validity_end = cdf.attrs['VALIDITY']
        if validity_start <= end and validity_end >= start:
            return [str(cdf.attrs['SOURCE'])]
        return []


class MJD2000TimeMixIn():
    """ MJD2000 mix-in class. """
    @staticmethod
    def _from_datetime(time):
        return datetime_to_mjd2000(time)

    @staticmethod
    def _to_datetime(time):
        return mjd2000_to_datetime(time)


class CdfEpochTimeMixIn():
    """ CDF_EPOCH mix-in class. """
    @staticmethod
    def _from_datetime(time):
        return datetime_to_cdf_rawtime(time, CDF_EPOCH_TYPE)

    @staticmethod
    def _to_datetime(time):
        return cdf_rawtime_to_datetime(time, CDF_EPOCH_TYPE)


def interpolate_time(source, time, time_field, fields, types=None,
                     nodata=None, bounds=None, min_len=2, **options):
    """ Read values of the listed fields from the given source and interpolate
    them at the given array of `time` values.
    The data exceeding the time interval of the source data is filled from the
    `nodata` dictionary. The function accepts additional keyword arguments which
    are passed to the `scipy.interpolate.interp1d` function (e.g., `kind`).
    """
    def _as_type(value, type_):
        return value.astype(type_) if type_ else value

    def _interpolate(field):
        return _as_type(interp1d(
            source_time,
            source(field, slice_),
            fill_value=nodata.get(field, nan),
            **options
        )(time), types.get(field))

    def _no_data(field):
        return full(
            time.shape,
            nodata.get(field, nan),
            types.get(field, "float")
        )

    if not fields:
        return {} # skip the data interpolation for an empty variable list

    if not nodata:
        nodata = {}

    if not types:
        types = {}

    # additional interpolation parameters
    options.update({
        'assume_sorted': True,
        'copy': False,
        'bounds_error': False,
    })

    source_time = source(time_field)

    # if possible get subset of the time data
    if time.size > 0 and source_time.size > min_len:
        start, stop = bounds if bounds else (time.min(), time.max())
        slice_ = array_slice(source_time, start, stop, min_len//2)
        source_time = source_time[slice_]
    else:
        slice_ = Ellipsis

    # check minimal length required by the chosen kind of interpolation
    if time.size > 0 and source_time.size >= min_len:
        return {field: _interpolate(field) for field in fields}
    return {field: _no_data(field) for field in fields}


def subset_time(source, start, stop, time_field, fields, margin=0):
    """ Extract subset of the listed `fields` from the given data source.
    The extracted range of values match times which lie within the given
    closed time interval. The time interval is defined by the `start` and
    `stop` values.
    The `margin` parameter is used to extend the index range by N surrounding
    elements. Negative margin is allowed.
    """
    if not fields:
        return {} # skip the data extraction for an empty variable list
    slice_ = array_slice(source(time_field), start, stop, margin)
    return {field: source(field, slice_) for field in fields}


def array_slice(values, start, stop, margin=0):
    """ Get sub-setting slice bounds. The sliced array must be sorted
    in the ascending order.
    """
    size = values.shape[0]
    idx_start, idx_stop = 0, size

    if start > stop:
        start, stop = stop, start

    if idx_stop > 0:
        idx_start = searchsorted(values, start, 'left')
        idx_stop = searchsorted(values, stop, 'right')

    if margin != 0:
        if idx_start < size:
            idx_start = min(size, max(0, idx_start - margin))
        if idx_stop > 0:
            idx_stop = min(size, max(0, idx_stop + margin))

    return slice(idx_start, idx_stop)
