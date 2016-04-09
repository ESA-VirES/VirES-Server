#-------------------------------------------------------------------------------
#
# CHAOS 5 - CORE, STATIC and Combined magnetic models
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

from eoxmagmod import (
    read_model_shc, DATA_CHAOS5_CORE_V4, DATA_CHAOS5_STATIC,
)
from vires.forward_models.base import BaseForwardModel

class CHAOS5CoreForwardModel(BaseForwardModel):
    """ Forward model calculator for the CHAOS-5 core field.
    """
    identifier = "CHAOS-5-Core"

    @property
    def model(self):
        return read_model_shc(DATA_CHAOS5_CORE_V4)


class CHAOS5StaticForwardModel(BaseForwardModel):
    """ Forward model calculator for the CHAOS-5 static field.
    """
    identifier = "CHAOS-5-Static"

    @property
    def model(self):
        return read_model_shc(DATA_CHAOS5_STATIC)


class CHAOS5CombinedForwardModel(BaseForwardModel):
    """ Forward model calculator for the CHAOS-5 Combined field.
    """
    identifier = "CHAOS-5-Combined"

    @property
    def model(self):
        return (
            read_model_shc(DATA_CHAOS5_CORE_V4) +
            read_model_shc(DATA_CHAOS5_STATIC)
        )

    @property
    def time_validity(self):
        """ Get the validity interval of the model. """
        return self._time_validity(read_model_shc(DATA_CHAOS5_CORE_V4))
