#-------------------------------------------------------------------------------
#
# IGRF magnetic models
#
# Project: VirES
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

from eoxmagmod.igrf import (
    read_model_igrf, read_model_shc, DATA_IGRF11, DATA_IGRF12,
)
from vires.forward_models.base import BaseForwardModel


class IGRF11ForwardModel(BaseForwardModel):
    """ Forward model calculator for the IGRF11.
    """
    identifier = "IGRF11"

    @property
    def model(self):
        return read_model_igrf(DATA_IGRF11)


class IGRF12Model(BaseForwardModel):
    """ Forward model calculator for the IGRF12.
    """
    identifier = "IGRF12"

    @property
    def model(self):
        return read_model_shc(DATA_IGRF12)


class IGRFForwardModel(IGRF12ForwardModel):
    """ Forward model calculator for the applicable IGRF model.
    """
    identifier = "IGRF"
