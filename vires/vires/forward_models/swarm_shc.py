#-------------------------------------------------------------------------------
#
# Swarm SHC models.
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

from django.conf import settings
from eoxmagmod import (
    load_model_shc,
    load_model_swarm_mma_2c_internal,
    load_model_swarm_mma_2c_external,
    load_model_swarm_mma_2f_geo_internal,
    load_model_swarm_mma_2f_geo_external,
    load_model_swarm_mio_internal,
    load_model_swarm_mio_external,
)
from vires.forward_models.base import BaseForwardModel
from vires.util import cached_property


class SwarmL2SHCForwardModel(BaseForwardModel):
    """ Base model for the Swarm L2 SHC models. """
    abstract = True
    product_type = None

    @cached_property
    def model(self):
        return load_model_shc(settings.VIRES_CACHED_PRODUCTS[self.product_type])


class SwarmMIO2CPrimaryForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MIO_SHA_2C product primary field model.
    """
    product_type = "MIO_SHA_2C"
    identifier = "MIO_SHA_2C-Primary"

    @cached_property
    def model(self):
        return load_model_swarm_mio_external(
            settings.VIRES_CACHED_PRODUCTS[self.product_type]
        )

class SwarmMIO2DPrimaryForwardModel(SwarmMIO2CPrimaryForwardModel):
    """ Swarm L2 MIO_SHA_2D product primary field model.
    """
    product_type = "MIO_SHA_2D"
    identifier = "MIO_SHA_2D-Primary"


class SwarmMIO2CSecondaryForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MIO_SHA_2C product secondary field model.
    """
    product_type = "MIO_SHA_2C"
    identifier = "MIO_SHA_2C-Secondary"

    @cached_property
    def model(self):
        return load_model_swarm_mio_internal(
            settings.VIRES_CACHED_PRODUCTS[self.product_type]
        )

class SwarmMIO2DSecondaryForwardModel(SwarmMIO2CSecondaryForwardModel):
    """ Swarm L2 MIO_SHA_2D product secondary field model.
    """
    product_type = "MIO_SHA_2D"
    identifier = "MIO_SHA_2D-Secondary"


class SwarmMMA2CPrimaryForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MMA_SHA_2C product primary field model.
    """
    product_type = "MMA_SHA_2C"
    identifier = "MMA_SHA_2C-Primary"

    @cached_property
    def model(self):
        return load_model_swarm_mma_2c_external(
            settings.VIRES_CACHED_PRODUCTS[self.product_type]
        )


class SwarmMMA2CSecondaryForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MMA_SHA_2C product secondary field model.
    """
    product_type = "MMA_SHA_2C"
    identifier = "MMA_SHA_2C-Secondary"

    @cached_property
    def model(self):
        return load_model_swarm_mma_2c_internal(
            settings.VIRES_CACHED_PRODUCTS[self.product_type]
        )


class SwarmMMA2FPrimaryForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MMA_SHA_2F product primary field model.
    """
    product_type = "MMA_SHA_2F"
    identifier = "MMA_SHA_2F-Primary"

    @cached_property
    def model(self):
        return load_model_swarm_mma_2f_geo_external(
            settings.VIRES_CACHED_PRODUCTS[self.product_type]
        )


class SwarmMMA2FSecondaryForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MMA_SHA_2F product secondary field model.
    """
    product_type = "MMA_SHA_2F"
    identifier = "MMA_SHA_2F-Secondary"

    @cached_property
    def model(self):
        return load_model_swarm_mma_2f_geo_internal(
            settings.VIRES_CACHED_PRODUCTS[self.product_type]
        )


class SwarmMCO2CForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MCO_SHA_2C product.
    """
    product_type = "MCO_SHA_2C"
    identifier = "MCO_SHA_2C"


class SwarmMCO2DForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MCO_SHA_2D product.
    """
    product_type = "MCO_SHA_2D"
    identifier = "MCO_SHA_2D"


class SwarmMCO2FForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MCO_SHA_2F product.
    """
    product_type = "MCO_SHA_2F"
    identifier = "MCO_SHA_2F"


class SwarmMLI2CForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MLI_SHA_2C product.
    """
    product_type = "MLI_SHA_2C"
    identifier = "MLI_SHA_2C"


class SwarmMLI2DForwardModel(SwarmL2SHCForwardModel):
    """ Swarm L2 MLI_SHA_2D product.
    """
    product_type = "MLI_SHA_2D"
    identifier = "MLI_SHA_2D"
