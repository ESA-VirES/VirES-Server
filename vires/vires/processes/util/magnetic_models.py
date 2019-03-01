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

from logging import getLogger
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

from vires.util import cached_property
from vires.file_util import FileChangeMonitor


DIPOLE_MODEL = "IGRF12"


class ModelFactory(object):
    """ Model factory class. """
    def __init__(self, loader, static_files=None, cached_files=None):
        self.loader = loader
        self.static_files = list(static_files or [])
        self.cached_files = list(cached_files or [])
        self._tracker = FileChangeMonitor()

    @cached_property
    def files(self):
        """ Get list of files required by this model. """
        cached_products = getattr(settings, "VIRES_CACHED_PRODUCTS", {})
        return self.static_files + [
            cached_products[source_id] for source_id in self.cached_files
        ]

    @property
    def model_changed(self):
        """ Check if the model files changed. """
        return self._tracker.changed(*self.files)

    def __call__(self):
        """ Create new model instance. """
        return self.loader(*self.files)


class ModelCache(object):
    """ Model cache class. """
    def __init__(self, model_factories, model_aliases=None, logger=None):
        self.logger = logger or getLogger(__name__)
        self.model_factories = model_factories
        self.model_aliases = model_aliases or {}
        self.cache = {}

    def __call__(self, model_id):
        """ Get model for given identifier. """
        model_id = self.model_aliases.get(model_id, model_id)

        model_factory = self.model_factories.get(model_id)
        if not model_factory:
            return None # invalid model id

        model = self.cache.get(model_id)
        if model_factory.model_changed or not model:
            self.cache[model_id] = model = model_factory()
            self.logger.info("%s model loaded", model_id)
        return model


MODEL_ALIASES = {
    "MCO_SHA_2X": "CHAOS-6-Core",
}


MODEL_FACTORIES = {
    "IGRF12": ModelFactory(
        lambda file_: load_model_shc(file_, interpolate_in_decimal_years=True),
        static_files=[IGRF12],
    ),
    "SIFM": ModelFactory(
        load_model_shc,
        static_files=[SIFM],
    ),
    "CHAOS-6-Static": ModelFactory(
        load_model_shc,
        static_files=[CHAOS6_STATIC],
    ),
    "CHAOS-6-Combined": ModelFactory(
        lambda static, core: load_model_shc_combined(
            static, core, to_mjd2000=decimal_year_to_mjd2000_simple
        ),
        static_files=[CHAOS6_STATIC],
        cached_files=["MCO_CHAOS6"],
    ),
    "CHAOS-6-Core": ModelFactory(
        lambda filename: load_model_shc(
            filename, to_mjd2000=decimal_year_to_mjd2000_simple
        ),
        cached_files=["MCO_CHAOS6"],
    ),
    "MCO_SHA_2C": ModelFactory(
        load_model_shc,
        cached_files=["MCO_SHA_2C"],
    ),
    "MCO_SHA_2D": ModelFactory(
        load_model_shc,
        cached_files=["MCO_SHA_2D"],
    ),
    "MCO_SHA_2F": ModelFactory(
        load_model_shc,
        cached_files=["MCO_SHA_2F"],
    ),
    "MLI_SHA_2C": ModelFactory(
        load_model_shc,
        cached_files=["MLI_SHA_2C"],
    ),
    "MLI_SHA_2D": ModelFactory(
        load_model_shc,
        cached_files=["MLI_SHA_2D"],
    ),
    "MMA_SHA_2C-Primary": ModelFactory(
        load_model_swarm_mma_2c_external,
        cached_files=["MMA_SHA_2C"],
    ),
    "MMA_SHA_2C-Secondary": ModelFactory(
        load_model_swarm_mma_2c_internal,
        cached_files=["MMA_SHA_2C"],
    ),
    "MMA_SHA_2F-Primary": ModelFactory(
        load_model_swarm_mma_2f_geo_external,
        cached_files=["MMA_SHA_2F"],
    ),
    "MMA_SHA_2F-Secondary": ModelFactory(
        load_model_swarm_mma_2f_geo_internal,
        cached_files=["MMA_SHA_2F"],
    ),
    "MIO_SHA_2C-Primary": ModelFactory(
        load_model_swarm_mio_external,
        cached_files=["MIO_SHA_2C"],
    ),
    "MIO_SHA_2C-Secondary": ModelFactory(
        load_model_swarm_mio_internal,
        cached_files=["MIO_SHA_2C"],
    ),
    "MIO_SHA_2D-Primary": ModelFactory(
        load_model_swarm_mio_external,
        cached_files=["MIO_SHA_2D"],
    ),
    "MIO_SHA_2D-Secondary": ModelFactory(
        load_model_swarm_mio_internal,
        cached_files=["MIO_SHA_2D"],
    ),
    "CHAOS-6-MMA-Primary": ModelFactory(
        load_model_swarm_mma_2c_external,
        cached_files=["MMA_CHAOS6"],
    ),
    "CHAOS-6-MMA-Secondary": ModelFactory(
        load_model_swarm_mma_2c_internal,
        cached_files=["MMA_CHAOS6"],
    ),
}

# list of all available models
MODEL_LIST = list(MODEL_FACTORIES) + list(MODEL_ALIASES)

get_model = ModelCache(MODEL_FACTORIES, MODEL_ALIASES)
