#-------------------------------------------------------------------------------
#
# Data Source - average magnetic field and polar current system
#
# Authors: Mikael Toresen <mikael.toresen@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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
#pylint: disable=too-many-locals,missing-docstring

from logging import getLogger, LoggerAdapter
from numpy import argsort, abs as aabs, nan, stack
from pyamps import AMPS
from vires.util import include, unique
from vires.cdf_util import CDF_DOUBLE_TYPE
from vires.dataset import Dataset
from .base import Model


class IonosphericCurrentModel(Model):
    """ Ionospheric current System in AMPS model. """
    DEFAULT_MODE = 0
    VECTOR_TRANSFORM_MODE = 1
    FILTER45_MODE = 2

    MODEL_PARAMETERS = [
        'IMF_V', 'IMF_BY_GSM', 'IMF_BZ_GSM', 'DipoleTiltAngle', 'F10'
    ]

    DEFAULT_REQUIRED_VARIABLES = [
        "Timestamp", "QDLat", "MLT", "QDBasis"
    ] + MODEL_PARAMETERS

    VARIABLES = {
        "DivergenceFreeCurrentFunction": (
            DEFAULT_MODE,
            AMPS.get_divergence_free_current_function,
            CDF_DOUBLE_TYPE, {
                'DESCRIPTION': 'AMPS - Divergence-free current function',
                'UNITS': 'kA'
            }
        ),
        "TotalCurrent": (
            VECTOR_TRANSFORM_MODE,
            AMPS.get_total_current,
            CDF_DOUBLE_TYPE, {
                'DESCRIPTION': 'AMPS - Total horizontal current',
                'UNITS': 'mA/m'
            }
        ),
        "UpwardCurrent": (
            FILTER45_MODE,
            AMPS.get_upward_current,
            CDF_DOUBLE_TYPE, {
                'DESCRIPTION': 'AMPS - Upward current',
                'UNITS': u'uA/m^2'
            }
        ),
    }

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return 'IonosphericCurrentModel: %s' % msg, kwargs

    def __init__(self, logger=None, varmap=None):
        super(IonosphericCurrentModel, self).__init__()
        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {})
        varmap = varmap or {}
        self._required_variables = [
            varmap.get(var, var) for var in self.DEFAULT_REQUIRED_VARIABLES
        ]

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
            times, qdlats, mlts, f_qd = (dataset[var] for var in req_var[:4])
            if times.size > 0:
                self.logger.debug("requested dataset length %s", len(times))
                idx = argsort(times)[times.size // 2] # median time index
                v_imf, by_imf, bz_imf, tilt, f107 = (
                    dataset[var][idx] for var in self.MODEL_PARAMETERS
                )
            else:
                v_imf, by_imf, bz_imf, tilt, f107 = 0., 0., 0., 0., 0.

            model = AMPS(
                v=v_imf, By=by_imf, Bz=bz_imf,
                tilt=tilt, f107=f107,
                resolution=0, dr=90,
            )

            for var in variables:
                mode, func, cdf_type, cdf_attr = self.VARIABLES[var]
                values = func(model, qdlats, mlts)
                if mode == self.VECTOR_TRANSFORM_MODE:
                    east, north = values
                    # 2D Coordinate transform: Quasi-Dipole -> Geographic
                    # NOTE: only for visualization purposes
                    values = stack((
                        f_qd[..., 0, 0] * east + f_qd[..., 1, 0] * north,
                        f_qd[..., 0, 1] * east + f_qd[..., 1, 1] * north
                    ), axis=-1)
                elif mode == self.FILTER45_MODE:
                    # Filter away values < 45 deg lat
                    values[aabs(qdlats) < 45] = nan
                output_ds.set(var, values, cdf_type, cdf_attr)

        return output_ds
