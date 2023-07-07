#-------------------------------------------------------------------------------
#
# Data Source - Swarm orbit counter time-series class
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
# pylint: disable=too-few-public-methods

from vires.cdf_util import CDF_INT1_TYPE, CDF_EPOCH_TYPE, convert_cdf_raw_times
from vires.orbit_direction import OrbitDirectionReader
from .auxiliary_data import AuxiliaryDataTimeSeries


class OrbitDirection(AuxiliaryDataTimeSeries):
    """ Orbit counter time-series class. """
    CDF_TYPE = {
        'OrbitDirection': CDF_INT1_TYPE, # uses 0 as NaN
        'OrbitDirectionBoundaryType': CDF_INT1_TYPE, # uses -1 as NaN
    }
    CDF_INTERP_TYPE = {
        'OrbitDirection': CDF_INT1_TYPE, # uses 0 as NaN
        'OrbitDirectionBoundaryType': CDF_INT1_TYPE, # uses -1 as NaN
    }
    CDF_ATTR = {
        'OrbitDirection': {
            'DESCRIPTION': (
                'Orbit direction in geographic coordinates (values: '
                '1 - ascending, -1 - descending, 0 - undefined)'
            ),
            'UNITS': '-',
        },
        'OrbitDirectionBoundaryType': {
            'DESCRIPTION': (
                'Boundary type of orbit direction in geographic coordinates '
                '(values: 1 - dataset start, 0 - latitude extremum, '
                '-1 - no coverage)'
                '1 - dataset start, 0 - latitude extremum, -1 - dataset end)'
            ),
            'UNITS': '-',
        }
    }
    TIME_VARIABLE = "Timestamp"

    @staticmethod
    def _encode_time(times, cdf_type):
        return convert_cdf_raw_times(times, cdf_type, CDF_EPOCH_TYPE)

    @staticmethod
    def _decode_time(times, cdf_type):
        return convert_cdf_raw_times(times, CDF_EPOCH_TYPE, cdf_type)

    def __init__(self, name, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, name, filename, OrbitDirectionReader, {
                'OrbitDirection': 'OrbitDirection',
                'BoundaryType': 'OrbitDirectionBoundaryType',
            }, logger
        )


class QDOrbitDirection(AuxiliaryDataTimeSeries):
    """ Orbit counter time-series class. """
    CDF_TYPE = {
        'QDOrbitDirection': CDF_INT1_TYPE, # uses 0 as NaN
        'QDOrbitDirectionBoundaryType': CDF_INT1_TYPE, # uses -1 as NaN
    }
    CDF_INTERP_TYPE = {
        'QDOrbitDirection': CDF_INT1_TYPE, # uses 0 as NaN
        'QDOrbitDirectionBoundaryType': CDF_INT1_TYPE, # uses -1 as NaN
    }
    CDF_ATTR = {
        'QDOrbitDirection': {
            'DESCRIPTION': (
                'Orbit direction in magnetic (QD) coordinates (values: '
                '1 - ascending, -1 - descending, 0 - undefined)'
            ),
            'UNITS': '-',
        },
        'QDOrbitDirectionBoundaryType': {
            'DESCRIPTION': (
                'Boundary type of orbit direction in magnetic (QD) coordinates '
                '(values: 1 - dataset start, 0 - latitude extremum, '
                '-1 - no coverage)'
            ),
            'UNITS': '-',
        }
    }
    TIME_VARIABLE = "Timestamp"

    @staticmethod
    def _encode_time(times, cdf_type):
        return convert_cdf_raw_times(times, cdf_type, CDF_EPOCH_TYPE)

    @staticmethod
    def _decode_time(times, cdf_type):
        return convert_cdf_raw_times(times, CDF_EPOCH_TYPE, cdf_type)

    def __init__(self, name, filename, logger=None):
        AuxiliaryDataTimeSeries.__init__(
            self, name, filename, OrbitDirectionReader, {
                'OrbitDirection': 'QDOrbitDirection',
                'BoundaryType': 'QDOrbitDirectionBoundaryType',
            }, logger
        )
