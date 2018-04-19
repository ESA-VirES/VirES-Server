#-------------------------------------------------------------------------------
#
# Data Source - solar position
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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
#pylint: disable=too-many-locals

from logging import getLogger, LoggerAdapter
from eoxmagmod import sunpos
from vires.util import include, unique
from vires.cdf_util import (
    cdf_rawtime_to_mjd2000,
    CDF_DOUBLE_TYPE,
)
from vires.dataset import Dataset
from .model import Model


class SunPosition(Model):
    """ Sun position model. """
    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "Latitude", "Longitude", "Radius",
    ]

    VARIABLES = {
        "SunDeclination": (0, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - declination', 'UNITS': 'deg',
        }),
        "SunRightAscension": (1, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - right ascension', 'UNITS': 'deg',
        }),
        "SunHourAngle": (2, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - hour angle', 'UNITS': 'deg',
        }),
        "SunAzimuthAngle": (3, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - azimuth angle', 'UNITS': 'deg',
        }),
        "SunZenithAngle": (4, CDF_DOUBLE_TYPE, {
            'DESCRIPTION': 'Sun position - zenith angle', 'UNITS': 'deg',
        }),
    }

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'SunPosition: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})

    @property
    def variables(self):
        return list(self.VARIABLES)

    @property
    def required_variables(self):
        return self._required_variables

    def eval(self, dataset, variables=None, **kwargs):
        variables = (
            self.variables if variables is None else
            list(include(unique(variables), self.variables))
        )
        self.logger.debug("requested variables %s", variables)

        output_ds = Dataset()

        if variables:
            req_var = self.required_variables
            # extract input data
            times, lats, lons, rads = (dataset[var] for var in req_var[:4])
            times_cdf_type = dataset.cdf_type.get(req_var[0], None)
            results = sunpos(
                cdf_rawtime_to_mjd2000(times, times_cdf_type),
                lats, lons,  # lat/lon in deg.
                rads * 1e-3, # radius in km
                0 # FIXME: UTC to TT offset
            )

            for variable in variables:
                idx, cdf_type, cdf_attr = self.VARIABLES[variable]
                output_ds.set(variable, result[idx], cdf_type, cdf_attr)

        return output_ds
