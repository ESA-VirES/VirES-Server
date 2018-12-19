#-------------------------------------------------------------------------------
#
# CHAOS 6 - CORE, STATIC and Combined magnetic models
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

from eoxmagmod import load_model_shc, load_model_shc_combined
from eoxmagmod.time_util import decimal_year_to_mjd2000_simple
from eoxmagmod.data import CHAOS6_STATIC
from vires.forward_models.base import BaseForwardModel
from vires.util import cached_property
from vires.forward_models.swarm_shc import SwarmL2SHCForwardModel


class CHAOS6CoreForwardModel(SwarmL2SHCForwardModel):
    """ Forward model calculator for the CHAOS-6 core field.
    """
    product_type = "MCO_CHAOS6"
    identifier = "CHAOS-6-Core"

    def laod_model(self):
        return load_model_shc(
            self.model_file, to_mjd2000=decimal_year_to_mjd2000_simple
        )


class CHAOS6StaticForwardModel(BaseForwardModel):
    """ Forward model calculator for the CHAOS-6 static field.
    """
    identifier = "CHAOS-6-Static"

    @cached_property
    def model(self):
        return load_model_shc(CHAOS6_STATIC)


class CHAOS6CombinedForwardModel(SwarmL2SHCForwardModel):
    """ Forward model calculator for the CHAOS-6 Combined field.
    """
    product_type = "MCO_CHAOS6"
    identifier = "CHAOS-6-Combined"

    def load_model(self):
        return load_model_shc_combined(
            self.model_file, CHAOS6_STATIC,
            to_mjd2000=decimal_year_to_mjd2000_simple
        )


class CHAOSCoreForwardModel(CHAOS6CoreForwardModel):
    """ Forward model calculator for the CHAOS core field.
    """
    identifier = "CHAOS-Core"


class MCO2FForwardModel(CHAOS6CoreForwardModel):
    """ Forward model calculator for the CHAOS core field.
    """
    identifier = "MCO_SHA_2X"


class CHAOSStaticForwardModel(CHAOS6StaticForwardModel):
    """ Forward model calculator for the CHAOS static field.
    """
    identifier = "CHAOS-Static"


class CHAOSCombinedForwardModel(CHAOS6CombinedForwardModel):
    """ Forward model calculator for the CHAOS Combined field.
    """
    identifier = "CHAOS-Combined"
