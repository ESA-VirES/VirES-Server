#-------------------------------------------------------------------------------
#
# Process Utilities - Load Magnetic Model
#
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from os.path import exists
from django.conf import settings
from eoxmagmod.data import CHAOS6_STATIC, IGRF12, SIFM
from eoxmagmod import (
    load_model_shc,
    load_model_shc_combined,
    load_model_swarm_mma_2c_internal,
    load_model_swarm_mma_2c_external,
    load_model_swarm_mma_2f_geo_internal,
    load_model_swarm_mma_2f_geo_external,
    load_model_swarm_mio_internal,
    load_model_swarm_mio_external,
)
from eoxmagmod.time_util import decimal_year_to_mjd2000_simple


MODELS_FACTORIES = {
    "IGRF12":
        lambda: load_model_shc(IGRF12, interpolate_in_decimal_years=True),
    "SIFM":
        lambda: load_model_shc(SIFM),
    "CHAOS-6-Static":
        lambda: load_model_shc(CHAOS6_STATIC),
}

CACHED_MODEL_LOADERS = {
    "CHAOS-6-Combined": lambda filename: load_model_shc_combined(
        filename, CHAOS6_STATIC, to_mjd2000=decimal_year_to_mjd2000_simple
    ),
    "CHAOS-6-Core": lambda filename: load_model_shc(
        filename, to_mjd2000=decimal_year_to_mjd2000_simple
    ),
    "MCO_SHA_2C": load_model_shc,
    "MCO_SHA_2D": load_model_shc,
    "MCO_SHA_2F": load_model_shc,
    "MLI_SHA_2C": load_model_shc,
    "MLI_SHA_2D": load_model_shc,
    "MMA_SHA_2C-Primary": load_model_swarm_mma_2c_external,
    "MMA_SHA_2C-Secondary": load_model_swarm_mma_2c_internal,
    "MMA_SHA_2F-Primary": load_model_swarm_mma_2f_geo_external,
    "MMA_SHA_2F-Secondary": load_model_swarm_mma_2f_geo_internal,
    "MIO_SHA_2C-Primary": load_model_swarm_mio_external,
    "MIO_SHA_2C-Secondary": load_model_swarm_mio_internal,
    "MIO_SHA_2D-Primary": load_model_swarm_mio_external,
    "MIO_SHA_2D-Secondary": load_model_swarm_mio_internal,
    "CHAOS-6-MMA-Primary": load_model_swarm_mma_2c_external,
    "CHAOS-6-MMA-Secondary": load_model_swarm_mma_2c_internal,
}
CACHED_MODEL_LOADERS["MCO_SHA_2X"] = CACHED_MODEL_LOADERS["CHAOS-6-Core"]

MODEL_SOURCES = {
    "MCO_SHA_2X": "MCO_CHAOS6",
    "CHAOS-6-Core": "MCO_CHAOS6",
    "CHAOS-6-Combined": "MCO_CHAOS6",
    "CHAOS-6-MMA-Primary": "MMA_CHAOS6",
    "CHAOS-6-MMA-Secondary": "MMA_CHAOS6",
    "MMA_SHA_2C-Primary": "MMA_SHA_2C",
    "MMA_SHA_2C-Secondary": "MMA_SHA_2C",
    "MMA_SHA_2F-Primary": "MMA_SHA_2F",
    "MMA_SHA_2F-Secondary": "MMA_SHA_2F",
    "MIO_SHA_2C-Primary": "MIO_SHA_2C",
    "MIO_SHA_2C-Secondary": "MIO_SHA_2C",
    "MIO_SHA_2D-Primary": "MIO_SHA_2D",
    "MIO_SHA_2D-Secondary": "MIO_SHA_2D",
}

# list of all available models
MODEL_LIST = list(MODELS_FACTORIES) + list(CACHED_MODEL_LOADERS)


def _get_cached_model(model_id):
    cached_products = getattr(settings, "VIRES_CACHED_PRODUCTS", {})
    try:
        loader = CACHED_MODEL_LOADERS[model_id]
        path = cached_products[MODEL_SOURCES.get(model_id, model_id)]
    except KeyError:
        return None
    return loader(path) if exists(path) else None


def get_model(model_id):
    """ Get model for given identifier. """
    read_model = MODELS_FACTORIES.get(model_id)
    if read_model:
        return read_model()
    else:
        return _get_cached_model(model_id)
