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
from eoxmagmod import (
    DATA_CHAOS6_CORE_X3, DATA_CHAOS6_STATIC,
    DATA_CHAOS5_CORE_V4, DATA_CHAOS5_STATIC,
    DATA_IGRF12, DATA_SIFM,
    read_model_wmm2015, read_model_wmm2010, read_model_emm2010,
    read_model_igrf11, read_model_shc,
)

MODELS_FACTORIES = {
    "CHAOS-6-Combined":
        lambda: (
            read_model_shc(DATA_CHAOS6_CORE_X3) +
            read_model_shc(DATA_CHAOS6_STATIC)
        ),
    "CHAOS-5-Combined":
        lambda: (
            read_model_shc(DATA_CHAOS5_CORE_V4) +
            read_model_shc(DATA_CHAOS5_STATIC)
        ),
    "IGRF12": lambda: read_model_shc(DATA_IGRF12),
    "IGRF11": read_model_igrf11,
    "IGRF": lambda: read_model_shc(DATA_IGRF12),
    "SIFM": lambda: read_model_shc(DATA_SIFM),
    "WMM": read_model_wmm2015,
    "WMM2010": read_model_wmm2010,
    "WMM2015": read_model_wmm2015,
    "EMM": read_model_emm2010,
    "EMM2010": read_model_emm2010,
    "CHAOS-6-Core": lambda: read_model_shc(DATA_CHAOS6_CORE_X3),
    "CHAOS-6-Static": lambda: read_model_shc(DATA_CHAOS6_STATIC),
    "CHAOS-5-Core": lambda: read_model_shc(DATA_CHAOS5_CORE_V4),
    "CHAOS-5-Static": lambda: read_model_shc(DATA_CHAOS5_STATIC),
}

CACHED_MODEL_LOADERS = {
    "MCO_SHA_2C": read_model_shc,
    "MCO_SHA_2D": read_model_shc,
    "MCO_SHA_2F": read_model_shc,
    "MLI_SHA_2C": read_model_shc,
    "MLI_SHA_2D": read_model_shc,
}


def _get_cached_model(model_id):
    cached_products = getattr(settings, "VIRES_CACHED_PRODUCTS", {})
    try:
        loader = CACHED_MODEL_LOADERS[model_id]
        path = cached_products.get[model_id]
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


def parse_model(input_id, model_id, shc, shc_input_id="shc"):
    """ Parse model identifier and returns the corresponding model."""
    if model_id == "Custom_Model":
        if shc is None:
            raise MissingRequiredInputError(shc_input_id)

        try:
            model = read_model_shc(shc)
        except ValueError:
            raise InvalidInputValueError(
                shc_input_id, "Failed to parse the custom model coefficients."
            )
    else:
        model = get_model(model_id)
        if model is None:
            raise InvalidInputValueError(
                input_id, "Invalid model identifier %r!" % model_id
            )
    return model


def parse_models(input_id, model_ids, shc, shc_input_id="shc"):
    """ Parse model identifiers and returns an ordered dictionary
    of the corresponding models.
    """
    models = OrderedDict()
    if model_ids.strip():
        for model_id in (id_.strip() for id_ in model_ids.split(",")):
            models[model_id] = parse_model(
                input_id, model_id, shc, shc_input_id
            )
    return models


def parse_models2(input_id, model_ids, shc, shc_input_id="shc"):
    """ Parse model identifiers and returns a list of the model sources. """
    models = parse_models(input_id, model_ids, shc, shc_input_id)
    return [MagneticModel(id_, model) for id_, model in models.iteritems()]
