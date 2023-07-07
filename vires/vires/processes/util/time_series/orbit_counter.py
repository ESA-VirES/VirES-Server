#-------------------------------------------------------------------------------
#
# Data Source - SWARM Orbit Counter time-series class
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
# pylint: disable=too-few-public-methods

from vires.cdf_util import (
    CDF_DOUBLE_TYPE, CDF_INT1_TYPE, CDF_INT4_TYPE,
)
from vires.cdf_util import mjd2000_to_cdf_rawtime
from vires.orbit_counter import OrbitCounterReader
from .base import TimeSeries
from .auxiliary_data import AuxiliaryDataTimeSeries


class OrbitCounter(AuxiliaryDataTimeSeries):
    """ Orbit counter time-series class. """
    CDF_TYPE = {
        'AscendingNodeTime': TimeSeries.TIMESTAMP_TYPE,
        'OrbitNumber': CDF_INT4_TYPE,               # uses -1 as NaN
        'AscendingNodeLongitude': CDF_DOUBLE_TYPE,   # NaN
        'OrbitSource': CDF_INT1_TYPE,               # uses -1 as NaN
    }
    CDF_INTERP_TYPE = {
        'AscendingNodeTime': TimeSeries.TIMESTAMP_TYPE,
        'OrbitNumber': CDF_INT4_TYPE,               # uses -1 as NaN
        'AscendingNodeLongitude': CDF_DOUBLE_TYPE,   # NaN
        'OrbitSource': CDF_INT1_TYPE,               # uses -1 as NaN
    }
    DATA_CONVERSION = {
        'AscendingNodeTime': (
            lambda data: mjd2000_to_cdf_rawtime(
                data, TimeSeries.TIMESTAMP_TYPE
            )
        ),
    }
    CDF_ATTR = {
        'AscendingNodeTime': {
            'DESCRIPTION': 'Time of the orbit ascending node.',
            'UNITS': '-',
        },
        'OrbitNumber': {
            'DESCRIPTION': 'Orbit number (set to -1 if not available)',
            'UNITS': '-',
        },
        'AscendingNodeLongitude': {
            'DESCRIPTION': (
                'Longitude of the orbit ascending node (set to NaN if not'
                ' avaiable)'
            ),
            'UNITS': 'deg',
        },
        'OrbitSource': {
            'DESCRIPTION': (
                'Source of orbit (values:'
                ' 0 - best quality; 1 - reduced quality; -1 - not available)'
            ),
            'UNITS': '-',
        },
    }
    TIME_VARIABLE = "Timestamp"

    def __init__(self, name, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, name, filename, OrbitCounterReader, {
                'orbit': 'OrbitNumber',
                'MJD2000': 'AscendingNodeTime',
                'phi_AN': 'AscendingNodeLongitude',
                'Source': 'OrbitSource',
            }, logger
        )
