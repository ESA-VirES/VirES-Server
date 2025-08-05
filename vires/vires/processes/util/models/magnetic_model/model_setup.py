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
# pylint: disable=too-many-arguments

from logging import getLogger
from collections import defaultdict
from vires.models import CachedMagneticModel, ProductCollection
from .residual import MagneticModelResidual
from .source_model import SourceMagneticModel
from .mio_model import MagneticModelMioMultiplication
from .cached_model  import ModelGapFill
from ...time_series import (
    ModelInterpolation,
    CachedModelExtraction,
    product_source_factory,
)

LOGGER = getLogger(__name__)


def generate_magnetic_model_sources(mission, spacecraft, grade,
                                    requested_models, source_models,
                                    no_cache=False, no_interpolation=False,
                                    master=None, interpolated_collection=None):
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
        no_interpolation: set to True to skip interpolation of non-cached models
        master: optional master time-series
        interpolated_collection: set to collection or collection id
            from which the model values should be interpolated
    """
    # ignore cache if explicitly requested by the master collection
    master_source = getattr(master, "source", None)
    #raise Exception(f"{master} {master_source}")
    if master_source:
        model_options = master_source.model_options
        if model_options.get("noCache", False):
            no_cache = True
        if model_options.get("interpolateFromCollection", None):
            interpolated_collection = model_options["interpolateFromCollection"]

    if no_interpolation:
        interpolated_collection = None

    if (
        interpolated_collection and
        not isinstance(interpolated_collection, ProductCollection)
    ):
        interpolated_collection = _get_collection(interpolated_collection)

    available_cached_models = {} if no_cache else _get_available_cached_models(
        mission, spacecraft, grade
    )

    # process source models required by the requested named composed models
    source_models = _handle_source_mio_models(source_models)
    source_models = _handle_cached_and_interpolated_models(
        models=source_models,
        available_cached_models=available_cached_models,
        master_source=master_source,
        interpolated_collection=interpolated_collection,
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
    models = defaultdict(list)
    for item in (grade or "").split("+"):
        for model in CachedMagneticModel.objects.filter(
            collection__spacecraft__mission=mission,
            collection__spacecraft__spacecraft=spacecraft,
            collection__grade=(item or None),
        ):
            models[model.name].append(model)
    return models


def _get_collection(collection_id):
    try:
        return ProductCollection.objects.get(identifier=collection_id)
    except ProductCollection.DoesNotExist:
        return None


def _handle_cached_and_interpolated_models(
    models, available_cached_models, master_source=None,
    interpolated_collection=None,
):
    """ If possible, replace cached source models with the cache extraction
    time-series object.
    """

    def _is_cached_model(model):
        return (
            isinstance(model, SourceMagneticModel) and
            model.name in available_cached_models
        )

    cached_models = defaultdict(list)
    interpolated_models = defaultdict(list)

    delayed_models = []

    # collect cached models, group them by collection and setup gap fillers
    for model in models:
        if isinstance(model, SourceMagneticModel):
            if model.name in available_cached_models:
                # cached source model
                collections = tuple(
                    model.collection
                    for model in available_cached_models[model.name]
                )
                cached_models[collections].append(model)
                delayed_models.append(ModelGapFill(model))
            elif interpolated_collection:
                # interpolated sources model
                interpolated_models[interpolated_collection].append(model)
                delayed_models.append(ModelGapFill(model))
            else:
                # non-cached non-interpolated source -> pass through
                yield model
        else: # non-source models -> retain after cached models
            delayed_models.append(model)

    # get per-collection cached model objects
    for collections, models_ in cached_models.items():

        # filter collections to match the master source
        if master_source:
            collections_subset = tuple(
                collection for collection in collections
                if collection in master_source.collections
            )
            if collections_subset:
                collections = collections_subset

        # filter mixed types collections
        collections = (collections[0], *(
            collection for collection in collections[1:]
            if collection.type == collections[0].type
        ))

        yield CachedModelExtraction(
            product_source_factory(collections),
            models_,
            master_source=master_source
        )

    # get per-collection interpolated model objects
    for collection, models_ in interpolated_models.items():
        yield ModelInterpolation(
            product_source_factory([collection]),
            models_,
            master_source=master_source
        )

    # release retained post-processing models
    yield from delayed_models


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
