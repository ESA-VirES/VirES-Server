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
#pylint: disable=too-many-arguments,missing-docstring

from vires.cdf_util import CDF_EPOCH_TYPE, CDF_DOUBLE_TYPE, CDF_UINT2_TYPE
from vires.aux_kp import KpReader
from vires.aux_dst import DstReader
from vires.aux_f107 import F10_2_Reader
from .auxiliary_data import AuxiliaryDataTimeSeries


class IndexKp10(AuxiliaryDataTimeSeries):
    """ Kp10 index time-series source class. """
    CDF_TYPE = {
        'Timestamp': CDF_EPOCH_TYPE,
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
        AuxiliaryDataTimeSeries.__init__(
            self, "Kp10", filename, KpReader,
            {'time': 'Timestamp', 'kp': 'Kp10'}, logger
        )


class IndexDst(AuxiliaryDataTimeSeries):
    """ Dst index time-series source class. """
    CDF_TYPE = {'Timestamp': CDF_EPOCH_TYPE, 'Dst': CDF_DOUBLE_TYPE}
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
        AuxiliaryDataTimeSeries.__init__(
            self, "Dst", filename, DstReader,
            {'time': 'Timestamp', 'dst': 'Dst'}, logger
        )


class IndexF107(AuxiliaryDataTimeSeries):
    """ F10.7 index (AUX_F10_2_) time-series source class. """
    CDF_TYPE = {'Timestamp': CDF_EPOCH_TYPE, 'F107': CDF_DOUBLE_TYPE}
    CDF_INTERP_TYPE = {'F107': CDF_DOUBLE_TYPE}
    CDF_ATTR = {
        'Timestamp': {
            'DESCRIPTION': 'Time stamp',
            'UNITS': '-',
        },
        'F107': {
            'DESCRIPTION': 'Assembled daily observed values of solar flux F10.7',
            'UNITS': '10e-22 W m^-2 Hz^-1',
        },
    }

    def __init__(self, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, "F107", filename, F10_2_Reader,
            {"MJD2000": 'Timestamp', "F10.7": 'F107'}, logger
        )
