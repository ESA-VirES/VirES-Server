#-------------------------------------------------------------------------------
#
# Data Source - rearrangements optimizing the model evaluation
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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
from .residual import MagneticModelResidual
from .source_model import SourceMagneticModel
from .mio_model import MagneticModelMioMultiplication

LOGGER = getLogger(__name__)


def generate_magnetic_model_sources(mission, spacecraft, requested_models,
                                    source_models, no_cache=False):
    """ Generate resolver models and other sources from the input
    model specification.

    Returns:
        List of models to be passed to the variable resolver.

    Args:
        mission: mission identifier
        spacecraft: mission spacecraft identifier (set to None if not Applicable)
        requested_models: list of the requested composed models
        source_models: list of the source models needed by the requested models
        no_cache: set to True to skip cached models
    """
    del mission, spacecraft, no_cache # reserved for future use

    # process source models required by the requested named composed models
    yield from _handle_source_mio_models(source_models)

    # process requested composed models
    for model in requested_models:
        yield model
        for variable in [
            *model.BASE_VARIABLES,
            *MagneticModelResidual.MODEL_VARIABLES
        ]:
            yield MagneticModelResidual(model.name, variable)


def _handle_source_mio_models(models):
    current_model_set = set()
    for model in models:

        new_source_model = model.source_model.raw_mio_model

        if not new_source_model:
            # not a MIO model
            if model.name not in current_model_set:
                current_model_set.add(model.name)
                yield model
            continue

        # create new source without the F10.7-factor multiplication
        new_model = SourceMagneticModel(new_source_model)

        # avoid duplicate models
        if new_model.name in current_model_set:
            continue

        current_model_set.add(new_model.name)
        yield new_model

        # for each variable create extra F10.7-factor multiplication
        for variable in model.BASE_VARIABLES:
            yield MagneticModelMioMultiplication(
                variable, model.name, new_model.name,
                wolf_ratio=_get_wolf_ratio(model.model),
            )


def _get_wolf_ratio(model):
    """ Extract Wolf ratio from the MIO model. """
    if hasattr(model, "wolf_ratio"):
        return model.wolf_ratio
    return model.model_above_ionosphere.wolf_ratio
