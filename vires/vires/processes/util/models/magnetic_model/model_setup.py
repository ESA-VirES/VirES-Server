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
from collections import defaultdict
from vires.models import CachedMagneticModel
from .residual import MagneticModelResidual
from .source_model import SourceMagneticModel
from .mio_model import MagneticModelMioMultiplication
from .cached_model  import CachedModelGapFill
from ...time_series import CachedModelExtraction

LOGGER = getLogger(__name__)


def generate_magnetic_model_sources(mission, spacecraft, grade,
                                    requested_models, source_models,
                                    no_cache=False, master=None):
    """ Generate resolver models and other sources from the input
    model specification.

    Returns:
        List of models and time-series to be passed to the variable resolver.

    Args:
        mission: mission identifier
        spacecraft: mission spacecraft identifier (set to None if not Applicable)
        requested_models: list of the requested composed models
        source_models: list of the source models needed by the requested models
        no_cache: set to True to skip cached models
        master: optional master time-series
    """
    # ignore cache if explicitly requested by the master collection
    master_collection = getattr(master, "collection", None)
    if master_collection:
        if (
            (master_collection.metadata.get("cachedMagneticModels") or {})
            .get("noCache", False)
        ):
            no_cache = True

    available_cached_models = _get_available_cached_models(
        mission, spacecraft, grade
    )

    # process source models required by the requested named composed models
    source_models = _handle_source_mio_models(source_models)
    if not no_cache:
        source_models = _handle_cached_models(
            source_models, available_cached_models,
            master_collection=master_collection,
        )
    yield from source_models

    # process requested composed models
    for model in requested_models:
        yield model
        for variable in [
            *model.BASE_VARIABLES,
            *MagneticModelResidual.MODEL_VARIABLES
        ]:
            yield MagneticModelResidual(model.name, variable)


def _get_available_cached_models(mission, spacecraft, grade):
    return {
        model.name: model
        for model in CachedMagneticModel.objects.filter(
            collection__spacecraft__mission=mission,
            collection__spacecraft__spacecraft=spacecraft,
            collection__grade=grade,
        )
    }


def _handle_cached_models(models, available_cached_models, master_collection=None):
    """ If possible, replace cached source models with the cache extraction
    time-series object.
    """

    def _is_cached_model(model):
        return (
            isinstance(model, SourceMagneticModel) and
            model.name in available_cached_models
        )

    cached_models = defaultdict(list)

    postproc_models = []

    # collect cached models, group them by collection and setup gap fillers
    for model in models:
        if isinstance(model, SourceMagneticModel):
            if model.name in available_cached_models: # cached source model
                collection = available_cached_models[model.name].collection
                cached_models[collection].append(model)
                postproc_models.append(CachedModelGapFill(model))
            else: # non-cached source -> pass through
                yield model
        else: # non-source models -> retain after cached models
            postproc_models.append(model)

    # get per-collection cached model objects
    for collection, models_ in cached_models.items():
        yield CachedModelExtraction(
            collection, models_,
            master_collection=master_collection
        )

    # release retained postprocessing models
    for model in postproc_models:
        yield model

def _handle_source_mio_models(models):
    """ Split source MIO models in two parts - source model without the F10.7
    multiplication and separate F10.7 multiplication.
    """
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
