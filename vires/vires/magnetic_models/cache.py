#-------------------------------------------------------------------------------
#
# Magnetic models - model cache class
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

from logging import getLogger


class ModelLoadError(Exception):
    """ Model error exception. """


class ModelCache():
    """ Model cache class.

    The cache prevent repeated slow loading of the magnetic models
    and reloads the models when the source model files got updated.

    The loading of the actual model and checks are handled by the model-specific
    model factory objects.
    """
    def __init__(self, model_factories, model_aliases=None, logger=None):
        self.logger = logger or getLogger(__name__)
        self.model_factories = model_factories
        self.model_aliases = model_aliases or {}
        self.cache = {}
        self.sources = {}

    def flush(self):
        """ Flush model cache. """
        self.cache = {}
        self.sources = {}

    def get_model(self, model_id):
        """ Get model for given identifier. """
        model, _ = self.get_model_with_sources(model_id)
        return model

    def get_model_with_sources(self, model_id):
        """ Get model with sources for given identifier. """
        model_id_orig = model_id
        model_id = self.model_aliases.get(model_id, model_id)

        model_factory = self.model_factories.get(model_id)
        if not model_factory:
            return None, None # invalid model id

        model = self.cache.get(model_id)
        if model_factory.model_changed or not model:
            try:
                model = model_factory()
            except Exception as error:
                self.logger.error(
                    "Error occurred wile loading model %s!",
                    model_id if model_id_orig == model_id
                    else f"{model_id_orig}({model_id})",
                    exc_info=True
                )
                raise ModelLoadError(
                    "Failed to load model %s!" % model_id_orig
                ) from error

            self.cache[model_id] = model
            self.sources[model_id] = sources = model_factory.sources
            self.logger.info("%s model loaded", model_id)
        else:
            sources = self.sources[model_id]
        return model, sources
