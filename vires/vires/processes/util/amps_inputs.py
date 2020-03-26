#-------------------------------------------------------------------------------
#
#  AMPS model inputs retrieval.
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
# pylint: disable=too-many-locals,too-many-arguments,missing-docstring

from django.conf import settings
from vires.dataset import Dataset
from vires.models import ProductCollection
from vires.cdf_util import CDF_EPOCH_TYPE, mjd2000_to_cdf_rawtime
from .models import SunPosition, SubSolarPoint, MagneticDipole, DipoleTiltAngle
from .time_series import ProductTimeSeries

IMF_BY_VARIABLE = "IMF_BY_GSM"
IMF_BZ_VARIABLE = "IMF_BZ_GSM"
IMF_V_VARIABLE = "IMF_V"


def get_amps_inputs(mjd2000):
    """ Get AMPS model inputs for the given MJD2000 time. """
    index_imf = ProductTimeSeries(
        ProductCollection.objects.get(type__identifier="SW_AUX_IMF_2_")
    )
    model_sun = SunPosition()
    model_subsol = SubSolarPoint()
    model_dipole = MagneticDipole()
    model_tilt_angle = DipoleTiltAngle()

    dataset = Dataset()
    dataset.set("Timestamp", [
        mjd2000_to_cdf_rawtime(mjd2000, CDF_EPOCH_TYPE)
    ], CDF_EPOCH_TYPE)
    dataset.set("Latitude", [0.0])
    dataset.set("Longitude", [0.0])
    dataset.set("Radius", [0.0])

    dataset.merge(index_imf.interpolate(dataset['Timestamp'], variables=[
        IMF_BY_VARIABLE, IMF_BZ_VARIABLE, IMF_V_VARIABLE
    ]))
    dataset.merge(model_sun.eval(dataset, ["SunDeclination", "SunHourAngle"]))
    dataset.merge(model_subsol.eval(dataset, ["SunVector"]))
    dataset.merge(model_dipole.eval(dataset, ["DipoleAxisVector"]))
    dataset.merge(model_tilt_angle.eval(dataset, ["DipoleTiltAngle"]))

    return {
        "imf_by": dataset[IMF_BY_VARIABLE][0],
        "imf_bz": dataset[IMF_BZ_VARIABLE][0],
        "imf_v": dataset[IMF_V_VARIABLE][0],
        "tilt_angle": dataset["DipoleTiltAngle"][0],
    }
