#-------------------------------------------------------------------------------
#
# Data Source - Kp, Dst and F10.7 indices
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-module-docstring

from vires.cdf_util import CDF_DOUBLE_TYPE, CDF_UINT2_TYPE
from vires.aux_kp import KpReader
from vires.aux_dst import DstReader, DDstReader
from vires.aux_f107 import F10_2_Reader
from .base import TimeSeries
from .base_auxiliary_data import BaseAuxiliaryDataTimeSeries


class IndexKp10(BaseAuxiliaryDataTimeSeries):
    """ Kp10 index time-series source class. """
    CDF_TYPE = {
        'Timestamp': TimeSeries.TIMESTAMP_TYPE,
        'Kp10': CDF_UINT2_TYPE,
    }
    CDF_INTERP_TYPE = {'Kp': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'Kp10': {
            'DESCRIPTION': 'Global geo-magnetic storm index multiplied by 10.',
            'UNITS': '-',
        },
    }

    def __init__(self, filename, logger=None):
        super().__init__(
            name="Kp10",
            reader=KpReader(filename),
            varmap={'time': 'Timestamp', 'kp': 'Kp10'},
            logger=logger,
        )


class IndexDDst(BaseAuxiliaryDataTimeSeries):
    """ Dst index time-series source class. """
    CDF_TYPE = {
        'Timestamp': TimeSeries.TIMESTAMP_TYPE,
        'Dst': CDF_DOUBLE_TYPE,
    }
    CDF_INTERP_TYPE = {'DDst': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'dDst': {
            'DESCRIPTION': (
                'Temporal change rate of the disturbance storm time index'
            ),
            'UNITS': 'nT/hour',
        },
    }

    def __init__(self, filename, logger=None):
        super().__init__(
            name="dDst",
            reader=DDstReader(filename),
            varmap={'time': 'Timestamp', 'ddst': 'dDst'},
            logger=logger,
        )


class IndexDst(BaseAuxiliaryDataTimeSeries):
    """ Dst index time-series source class. """
    CDF_TYPE = {
        'Timestamp': TimeSeries.TIMESTAMP_TYPE,
        'Dst': CDF_DOUBLE_TYPE,
    }
    CDF_INTERP_TYPE = {'Dst': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'Dst': {
            'DESCRIPTION': 'Disturbance storm time index',
            'UNITS': 'nT',
        },
    }

    def __init__(self, filename, logger=None):
        super().__init__(
            name="Dst",
            reader=DstReader(filename),
            varmap={'time': 'Timestamp', 'dst': 'Dst'},
            logger=logger,
        )


class IndexF107(BaseAuxiliaryDataTimeSeries):
    """ F10.7 index (AUX_F10_2_) time-series source class. """
    CDF_TYPE = {
        'Timestamp': TimeSeries.TIMESTAMP_TYPE,
        'F107': CDF_DOUBLE_TYPE,
        'F107_avg81d': CDF_DOUBLE_TYPE,
        'F107_avg81d_count': CDF_DOUBLE_TYPE,
    }
    CDF_INTERP_TYPE = {
        'F107': CDF_DOUBLE_TYPE,
        'F107_avg81d': CDF_DOUBLE_TYPE,
        'F107_avg81d_count': CDF_DOUBLE_TYPE,
    }
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'F107': {
            'DESCRIPTION': 'Assembled daily observed values of solar flux F10.7',
            'UNITS': '10e-22 W m^-2 Hz^-1',
        },
        'F107_avg81d': {
            'DESCRIPTION': (
                '81-days moving average of the assembled daily observed values'
                ' of solar flux F10.7'
            ),
            'UNITS': '10e-22 W m^-2 Hz^-1',
        },
        'F107_avg81d_count': {
            'DESCRIPTION': (
                '81-days moving average window sample count, excluding no-data'
                ' values'
            ),
            'UNITS': '-',
        },
    }
    VARIABLE_NAME_MAPPING = {
        'MJD2000': 'Timestamp',
        'F10.7': 'F107',
        'F10.7_avg81d': 'F107_avg81d',
        'F10.7_avg81d_count': 'F107_avg81d_count',
    }

    def __init__(self, filename, logger=None):
        super().__init__(
            name="F107",
            reader=F10_2_Reader(filename),
            varmap=self.VARIABLE_NAME_MAPPING,
            logger=logger
        )
