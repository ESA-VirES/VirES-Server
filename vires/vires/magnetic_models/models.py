#-------------------------------------------------------------------------------
#
# Magnetic models - definition of all available magnetic models
#
# Authors: Martin Paces <martin.paces@eox.at>
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
#pylint: disable=too-few-public-methods

from os.path import basename, splitext
from logging import getLogger
from numpy import inf
from pyamps.model_utils import default_coeff_fn as AMPS
from eoxmagmod.data import (
    CHAOS_STATIC_LATEST,
    IGRF_LATEST,
    IGRF_LATEST_SOURCE,
    LCS1,
    MF7,
)
from eoxmagmod import (
    load_model_shc,
    load_model_swarm_mma_2c_internal,
    load_model_swarm_mma_2c_external,
    load_model_swarm_mma_2f_geo_internal,
    load_model_swarm_mma_2f_geo_external,
    load_model_swarm_mio_internal,
    load_model_swarm_mio_external,
)
from eoxmagmod.time_util import decimal_year_to_mjd2000
from eoxmagmod.magnetic_model.parser_shc import parse_shc_header
from ..amps import AmpsMagneticFieldModel
from ..util import cached_property
from .files import (
    ModelFileWithLiteralSource,
    CachedModelFileWithSourceFile,
    CachedComposedModelFile,
    CachedZippedMultiModelFile,
)
from .factories import ModelFactory, ZippedModelFactory
from .cache import ModelCache


DIPOLE_MODEL = "IGRF"
CHAOS_STATIC_SOURCE = basename(CHAOS_STATIC_LATEST)
LCS1_SOURCE = basename(LCS1)
MF7_SOURCE = basename(MF7)
AMPS_SOURCE = basename(splitext(AMPS)[0])

MODEL_ALIASES = {}

PREDEFINED_COMPOSED_MODELS = {
    "MCO_SHA_2X": "'CHAOS-Core'",
    "CHAOS": "'CHAOS-Core' + 'CHAOS-Static' + 'CHAOS-MMA-Primary' + 'CHAOS-MMA-Secondary'",
    "CHAOS-MMA": "'CHAOS-MMA-Primary' + 'CHAOS-MMA-Secondary'",
    "MMA_SHA_2C": "'MMA_SHA_2C-Primary' + 'MMA_SHA_2C-Secondary'",
    "MMA_SHA_2F": "'MMA_SHA_2F-Primary' + 'MMA_SHA_2F-Secondary'",
    "_MIO_SHA_2C": "'_MIO_SHA_2C-Primary' + '_MIO_SHA_2C-Secondary'",
    "_MIO_SHA_2D": "'_MIO_SHA_2D-Primary' + '_MIO_SHA_2D-Secondary'",
    "MIO_SHA_2C": "'MIO_SHA_2C-Primary' + 'MIO_SHA_2C-Secondary'",
    "MIO_SHA_2D": "'MIO_SHA_2D-Primary' + 'MIO_SHA_2D-Secondary'",
    "SwarmCI": (
        "MCO_SHA_2C + MLI_SHA_2C"
        "+ 'MMA_SHA_2C-Primary' + 'MMA_SHA_2C-Secondary'"
        "+ 'MIO_SHA_2C-Primary' + 'MIO_SHA_2C-Secondary'"
    )
}


def mio_loader_without_f107(mio_loader, removed_parameter="f107"):
    """  Special wrapper of the MIO model loader stripping F10.7 requirement.
    As result of this the model will not be multiplied by the (1 + N*F10.7)
    factor.
    """
    def _mio_loader_without_f107(*args, **kwargs):
        model = mio_loader(*args, **kwargs)
        model.parameters = tuple(
            parameter for parameter in model.parameters
            if parameter != removed_parameter
        )
        return model
    return _mio_loader_without_f107


def shc_validity_reader(file_):
    """ SHC model validity reader. """
    return _shc_validity_reader(file_, decimal_year_to_mjd2000)


def _shc_validity_reader(file_, to_mjd2000):
    """ Low-level SHC model validity reader. """
    if hasattr(file_, 'read'):
        header = parse_shc_header(file_)
    else:
        with open(file_) as file_in:
            header = parse_shc_header(file_in)
    return (
        to_mjd2000(header["validity_start"]), to_mjd2000(header["validity_end"])
    )


def mio_validity_reader(_):
    """ MIO model validity reader. """
    return (-inf, +inf)


MODEL_FACTORIES = {
    "IGRF": ModelFactory(
        lambda file_: load_model_shc(file_, interpolate_in_decimal_years=True),
        [ModelFileWithLiteralSource(IGRF_LATEST, IGRF_LATEST_SOURCE, shc_validity_reader)]
    ),
    "CHAOS-Static": ModelFactory(
        load_model_shc,
        [ModelFileWithLiteralSource(
            CHAOS_STATIC_LATEST, CHAOS_STATIC_SOURCE, shc_validity_reader
        )]
    ),
    "CHAOS-Core": ZippedModelFactory(
        load_model_shc,
        CachedZippedMultiModelFile("MCO_SHA_2X", shc_validity_reader)
    ),
    "LCS-1": ModelFactory(
        load_model_shc,
        [ModelFileWithLiteralSource(LCS1, LCS1_SOURCE, shc_validity_reader)]
    ),
    "MF7": ModelFactory(
        load_model_shc,
        [ModelFileWithLiteralSource(MF7, MF7_SOURCE, shc_validity_reader)]
    ),
    "MCO_SHA_2C": ModelFactory(
        load_model_shc,
        [CachedModelFileWithSourceFile("MCO_SHA_2C", shc_validity_reader)]
    ),
    "MCO_SHA_2D": ModelFactory(
        load_model_shc,
        [CachedModelFileWithSourceFile("MCO_SHA_2D", shc_validity_reader)]
    ),
    "MLI_SHA_2C": ModelFactory(
        load_model_shc,
        [CachedModelFileWithSourceFile("MLI_SHA_2C", shc_validity_reader)]
    ),
    "MLI_SHA_2D": ModelFactory(
        load_model_shc,
        [CachedModelFileWithSourceFile("MLI_SHA_2D", shc_validity_reader)]
    ),
    "MLI_SHA_2E": ModelFactory(
        load_model_shc,
        [CachedModelFileWithSourceFile("MLI_SHA_2E", shc_validity_reader)]
    ),
    "MMA_SHA_2C-Primary": ModelFactory(
        load_model_swarm_mma_2c_external,
        [CachedComposedModelFile("MMA_SHA_2C")]
    ),
    "MMA_SHA_2C-Secondary": ModelFactory(
        load_model_swarm_mma_2c_internal,
        [CachedComposedModelFile("MMA_SHA_2C")]
    ),
    "MMA_SHA_2F-Primary": ModelFactory(
        load_model_swarm_mma_2f_geo_external,
        [CachedComposedModelFile("MMA_SHA_2F")]
    ),
    "MMA_SHA_2F-Secondary": ModelFactory(
        load_model_swarm_mma_2f_geo_internal,
        [CachedComposedModelFile("MMA_SHA_2F")]
    ),
    "_MIO_SHA_2C-Primary": ModelFactory(
        mio_loader_without_f107(load_model_swarm_mio_external),
        [CachedModelFileWithSourceFile("MIO_SHA_2C", mio_validity_reader)]
    ),
    "_MIO_SHA_2C-Secondary": ModelFactory(
        mio_loader_without_f107(load_model_swarm_mio_internal),
        [CachedModelFileWithSourceFile("MIO_SHA_2C", mio_validity_reader)]
    ),
    "_MIO_SHA_2D-Primary": ModelFactory(
        mio_loader_without_f107(load_model_swarm_mio_external),
        [CachedModelFileWithSourceFile("MIO_SHA_2D", mio_validity_reader)]
    ),
    "_MIO_SHA_2D-Secondary": ModelFactory(
        mio_loader_without_f107(load_model_swarm_mio_internal),
        [CachedModelFileWithSourceFile("MIO_SHA_2D", mio_validity_reader)]
    ),
    "MIO_SHA_2C-Primary": ModelFactory(
        load_model_swarm_mio_external,
        [CachedModelFileWithSourceFile("MIO_SHA_2C", mio_validity_reader)]
    ),
    "MIO_SHA_2C-Secondary": ModelFactory(
        load_model_swarm_mio_internal,
        [CachedModelFileWithSourceFile("MIO_SHA_2C", mio_validity_reader)]
    ),
    "MIO_SHA_2D-Primary": ModelFactory(
        load_model_swarm_mio_external,
        [CachedModelFileWithSourceFile("MIO_SHA_2D", mio_validity_reader)]
    ),
    "MIO_SHA_2D-Secondary": ModelFactory(
        load_model_swarm_mio_internal,
        [CachedModelFileWithSourceFile("MIO_SHA_2D", mio_validity_reader)]
    ),
    "CHAOS-MMA-Primary": ModelFactory(
        load_model_swarm_mma_2c_external,
        [CachedComposedModelFile("MMA_CHAOS_")]
    ),
    "CHAOS-MMA-Secondary": ModelFactory(
        load_model_swarm_mma_2c_internal,
        [CachedComposedModelFile("MMA_CHAOS_")]
    ),
    "AMPS": ModelFactory(
        AmpsMagneticFieldModel,
        [ModelFileWithLiteralSource(
            AMPS, AMPS_SOURCE, lambda _: AmpsMagneticFieldModel.validity
        )]
    ),
}

# MIO MODELS multiplied by the (1 + N*F10.7) factor and their mapping
# to models without the multiplication factor

MIO_MODELS = {
    "MIO_SHA_2C": "_MIO_SHA_2C",
    "MIO_SHA_2D": "_MIO_SHA_2D",
    "MIO_SHA_2C-Primary": "_MIO_SHA_2C-Primary",
    "MIO_SHA_2C-Secondary": "_MIO_SHA_2C-Secondary",
    "MIO_SHA_2D-Primary": "_MIO_SHA_2D-Primary",
    "MIO_SHA_2D-Secondary": "_MIO_SHA_2D-Secondary",
}

# list of all available models
MODEL_LIST = (
    list(MODEL_FACTORIES)
    + list(MODEL_ALIASES)
    + list(PREDEFINED_COMPOSED_MODELS)
)


MODEL_CACHE = ModelCache(MODEL_FACTORIES, MODEL_ALIASES, getLogger(__name__))
