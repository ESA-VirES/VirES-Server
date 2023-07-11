#-------------------------------------------------------------------------------
#
# Model expression and list parser
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
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

from itertools import chain
from eoxmagmod import load_model_shc
from vires.parsers.exceptions import ParserError
from vires.parsers.model_list_parser import get_model_list_parser
from vires.parsers.model_list_lexer import get_model_list_lexer
from vires.parsers.model_expression_parser import get_model_expression_parser
from vires.parsers.model_expression_lexer import get_model_expression_lexer
from .models import MODEL_CACHE, PREDEFINED_COMPOSED_MODELS
from .source_model import SourceMagneticModel
from .composed_model import ComposedMagneticModel


CUSTOM_MODEL_NAME = "Custom_Model"


def lazy_model_loader(model_id, model_expression):
    """ Lazy loader for pre-defined models. """
    def _load_predefined_model():
        parser = ModelInputParser()
        parser.parse_model_expression(model_expression, model_id)
        return parser.parsed_models[-1], parser.source_models.values()
    return _load_predefined_model


PREDEFINED_MODELS = {
    model_id: lazy_model_loader(model_id, model_expression)
    for model_id, model_expression in PREDEFINED_COMPOSED_MODELS.items()
}


class ModelInputParser:
    """ Class parsing the model list. """
    SourceMagneticModel = SourceMagneticModel
    ComposedMagneticModel = ComposedMagneticModel

    class ParsingError(Exception):
        """ Model parsing error. """

    def __init__(self):
        self.parsed_models = []
        self.known_models = {}
        self.source_models = {}
        self.custom_models = {}

    def parse_custom_model(self, shc_coefficients, model_id=CUSTOM_MODEL_NAME):
        """ Parse custom model input from a file-like object and add it
        to the known models. This models will be recognized later in the parsed
        model expressions.
        """
        model_obj = self._parse_custom_model(model_id, shc_coefficients)
        if model_obj is not None:
            self.custom_models[model_obj.identifier] = model_obj

    def parse_model_expression(self, model_expression, model_id=None):
        """ Parse model expression input. The parsed composed model is added
        to the parsed models.
        Optionally, a model identifier can be assigned to the model.
        """
        if model_id is None:
            model_id = "<nameless>"
        model_components = self.parse_model_expression_string(model_expression)
        self.parsed_models.append(
            self._process_composed_model(model_id, model_components)
        )

    def parse_model_list(self, model_list):
        """ Parse model list input. The parsed list model is then returned.
        Earlier model definitions are recognized in the later model expressions.
        """
        self.parsed_models.extend(
            self._process_composed_model(model_def.id, model_def.components)
            for model_def in self.parse_model_list_string(model_list)
        )

    def _process_composed_model(self, model_id, model_components):
        self.known_models[model_id] = model_obj = self.ComposedMagneticModel(
            model_id,
            list(chain.from_iterable(
                self._process_model_component(component)
                for component in model_components
            ))
        )
        return model_obj

    def _process_model_component(self, model_def):

        def _create_source_model(model_id, model, sources, params):
            model_obj = self.SourceMagneticModel(
                model_id, model, sources, params
            )
            self.source_models[model_obj.name] = model_obj
            return model_obj

        def _unpack_source_models(scale, composed_model_obj):
            for component in composed_model_obj.components:
                yield Component(scale * component.scale, component.model)

        Component = self.ComposedMagneticModel.Component
        model_id = model_def.id
        parameters = model_def.parameters.copy()
        scale = parameters.pop("scale", 1)

        if model_id in self.known_models:
            # already known composed model
            model_obj = self.known_models.get(model_id)
            self._assert_no_parameter(model_id, parameters)
            yield from _unpack_source_models(scale, model_obj)

        elif model_id in PREDEFINED_MODELS:
            # predefined composed model
            model_obj, source_models = PREDEFINED_MODELS[model_id]()
            self._assert_no_parameter(model_id, parameters)
            self.source_models.update((src.name, src) for src in source_models)
            yield from _unpack_source_models(scale, model_obj)

        elif model_id in self.custom_models:
            # custom source model
            model_obj = self.custom_models.get(model_id)
            model_obj = _create_source_model(
                model_id, model_obj.model, model_obj.sources,
                self._get_model_parameters(
                    model_id, model_obj.model, parameters,
                    model_obj.parameters,
                )
            )
            yield Component(scale, model_obj)

        else:
            # new source model
            model, sources = MODEL_CACHE.get_model_with_sources(model_def.id)
            if model is None:
                raise self.ParsingError(
                    f"Invalid model identifier {model_def.id!r}!"
                )

            model_obj = _create_source_model(
                model_id, model, self._retype_sources(sources),
                self._get_model_parameters(
                    model_id, model, parameters,
                    self._get_model_defauls(model)
                )
            )

            yield Component(scale, model_obj)

    def _get_model_defauls(self, model):
        extract = {
            "min_degree": lambda m, k: m.min_degree,
            "max_degree": lambda m, k: m.degree,
        }
        expected = self._get_user_parameter_names(model)
        return {
            key: extract.get(key, getattr)(model, key) for key in expected
        }

    def _get_model_parameters(self, model_id, model, parameters, defaults):
        expected = self._get_user_parameter_names(model)
        self._assert_no_parameter(model_id, set(parameters).difference(expected))

        result = {}
        result.update(defaults)
        result.update(parameters)

        if "min_degree" in result:
            result["min_degree"] = max(result["min_degree"], defaults["min_degree"])

        if "max_degree" in result:
            max_degree = min(result["max_degree"], defaults["max_degree"])
            if max_degree >= 0:
                result["max_degree"] = max_degree

        if "min_degree" in result and "max_degree" in result:
            result["min_degree"] = min(result["min_degree"], result["max_degree"])

        return result

    @staticmethod
    def _get_user_parameter_names(model):
        return getattr(
            model, 'user_parameters', ("min_degree", "max_degree")
        )

    def _assert_no_parameter(self, model_id, parameters):
        for parameter in parameters:
            raise self.ParsingError(
                f"The model {model_id} does not accept the {parameter} parameter!"
            )

    def _parse_custom_model(self, model_id, shc_coefficients, sources=None):
        if shc_coefficients is None:
            return None
        try:
            model = load_model_shc(shc_coefficients)
        except ValueError:
            raise self.ParsingError(
                "Failed to parse the custom model coefficients."
            ) from None

        return self.SourceMagneticModel(
            model_id, model, self._retype_sources(sources or []),
            {
                "min_degree": model.min_degree,
                "max_degree": model.degree
            }
        )

    @staticmethod
    def _retype_sources(sources):
        return [SourceMagneticModel.Sources(*item) for item in sources]

    def parse_model_expression_string(self, model_expression_string):
        """ Low-level model expression parser. """
        lexer = get_model_expression_lexer()
        parser = get_model_expression_parser()
        try:
            return parser.parse(model_expression_string, lexer=lexer)
        except ParserError as error:
            raise self.ParsingError(f"Invalid model expression! {error}")

    def parse_model_list_string(self, model_list_string):
        """ Low-level model list parser. """
        lexer = get_model_list_lexer()
        parser = get_model_list_parser()
        try:
            return parser.parse(model_list_string, lexer=lexer)
        except ParserError as error:
            raise self.ParsingError(f"Invalid model list! {error}")
