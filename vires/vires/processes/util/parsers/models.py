#-------------------------------------------------------------------------------
#
# Process Utilities - models input parsers
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=too-many-branches,unused-argument

from itertools import chain
from eoxmagmod import load_model_shc
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.magnetic_models import MODEL_CACHE, PREDEFINED_COMPOSED_MODELS
from vires.parsers.exceptions import ParserError
from vires.parsers.model_list_parser import get_model_list_parser
from vires.parsers.model_list_lexer import get_model_list_lexer
from vires.parsers.model_expression_parser import get_model_expression_parser
from vires.parsers.model_expression_lexer import get_model_expression_lexer
from ..models import SourceMagneticModel, ComposedMagneticModel


PREDEFINED_MODELS = {}


def lazy_model_loader(model_id, model_expression):
    """ Lazy loader for pre-defined models. """
    def _load_predefined_model():
        parser = ModelInputParser()
        model_obj = parser.parse_model_expression(model_expression, model_id)
        return model_obj, parser.source_models.values()
    return _load_predefined_model


PREDEFINED_MODELS.update(
    (model_id, lazy_model_loader(model_id, model_expression))
    for model_id, model_expression in PREDEFINED_COMPOSED_MODELS.items()
)


def parse_model_expression(input_id, model_input, shc=None, shc_input_id="shc"):
    """ Parse model expression and returns the final composed model and
    a list of model sources.
    """
    parser = ModelInputParser()
    try:
        parser.parse_custom_model(shc)
    except parser.ParsingError as error:
        raise InvalidInputValueError(shc_input_id, str(error))
    try:
        model_obj = parser.parse_model_expression(model_input)
    except parser.ParsingError as error:
        raise InvalidInputValueError(input_id, str(error))
    return model_obj, parser.source_models.values()


def parse_model_list(input_id, models_input, shc=None, shc_input_id="shc"):
    """ Parse list of model and return a list of named composed models and
    source models.
    """
    parser = ModelInputParser()
    try:
        parser.parse_custom_model(shc)
    except parser.ParsingError as error:
        raise InvalidInputValueError(shc_input_id, str(error))
    try:
        parser.parse_model_list(models_input)
    except parser.ParsingError as error:
        raise InvalidInputValueError(input_id, str(error))
    return parser.requested_models, parser.source_models.values()


class ModelInputParser:
    """ Class parsing the model list. """

    class ParsingError(Exception):
        """ Model parsing error. """

    def __init__(self):
        self.requested_models = []
        self.known_models = {}
        self.source_models = {}

    def parse_custom_model(self, shc_coefficients):
        """ Parse custom model input. """
        custom_model = self._parse_custom_model(shc_coefficients)
        if custom_model is not None:
            self.known_models[custom_model.name] = custom_model

    def parse_model_expression(self, model_expression, model_id=None):
        """ Parse model expression input. """
        if model_id is None:
            model_id = "<nameless>"
        model_components = self._parse_model_expression_string(model_expression)
        model_obj = self._process_composed_model(model_id, model_components)
        self.requested_models.append(model_obj)
        return model_obj

    def parse_model_list(self, model_list):
        """ Parse model list input. """
        for model_def in self._parse_model_list_string(model_list):
            self.requested_models.append(
                self._process_composed_model(model_def.id, model_def.components)
            )

    def _process_composed_model(self, model_id, model_components):
        model_obj = ComposedMagneticModel(model_id, list(chain.from_iterable(
            self._process_model_component(component)
            for component in model_components
        )))
        self.known_models[model_id] = model_obj
        return model_obj

    def _assert_no_parameter(self, model_id, parameters):
        for parameter in parameters:
            raise self.ParsingError(
                "The model %s does not accept the %s parameter!"
                % (model_id, parameter)
            )

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

    def _get_model_defauls(self, model):
        extract = {
            "min_degree": lambda m, k: m.min_degree,
            "max_degree": lambda m, k: m.degree,
        }
        expected = self._get_user_parameter_names(model)
        return {
            key: extract.get(key, getattr)(model, key) for key in expected
        }

    @staticmethod
    def _get_user_parameter_names(model):
        return getattr(
            model, 'user_parameters', ("min_degree", "max_degree")
        )

    def _process_model_component(self, model_def):

        def _create_source_model(model_id, model, sources, params):
            model_obj = SourceMagneticModel(model_id, model, sources, params)
            self.source_models[model_obj.name] = model_obj
            return model_obj

        model_id = model_def.id
        parameters = model_def.parameters.copy()
        scale = parameters.pop("scale", 1)

        model_obj = self.known_models.get(model_id)

        if model_obj is None and model_id in PREDEFINED_MODELS:
            self._assert_no_parameter(model_id, parameters)
            model_obj, sources = PREDEFINED_MODELS[model_id]()
            self.source_models.update((src.name, src) for src in sources)
            for component_scale, component in model_obj.components:
                yield scale*component_scale, component
            return

        if model_obj is not None:
            if (
                    isinstance(model_obj, ComposedMagneticModel) and
                    len(model_obj.components) == 1
                ):
                model_scale, model_obj = model_obj.components[0]
                scale *= model_scale

            if isinstance(model_obj, SourceMagneticModel):
                model_obj = _create_source_model(
                    model_id, model_obj.model, model_obj.sources,
                    self._get_model_parameters(
                        model_id, model_obj.model, parameters,
                        model_obj.parameters
                    )
                )
            else:
                self._assert_no_parameter(model_id, parameters)

        else: # new source model
            model, sources = MODEL_CACHE.get_model_with_sources(model_def.id)
            if model is None:
                raise self.ParsingError(
                    "Invalid model identifier %r!" % model_def.id
                )

            model_obj = _create_source_model(
                model_id, model, sources, self._get_model_parameters(
                    model_id, model, parameters, self._get_model_defauls(model)
                )
            )

        yield scale, model_obj

    def _parse_custom_model(self, shc_coefficients):
        if shc_coefficients is None:
            return None
        try:
            model = load_model_shc(shc_coefficients)
        except ValueError:
            raise self.ParsingError(
                "Failed to parse the custom model coefficients."
            )
        return ComposedMagneticModel("Custom_Model", [
            # NOTE: no source set for the custom model
            (1.0, SourceMagneticModel(
                "Custom_Model", model, [], {
                    "min_degree": model.min_degree, "max_degree": model.degree
                }
            ))
        ])

    def _parse_model_expression_string(self, model_expression_string):
        lexer = get_model_expression_lexer()
        parser = get_model_expression_parser()
        try:
            return parser.parse(model_expression_string, lexer=lexer)
        except ParserError as error:
            raise self.ParsingError("Invalid model expression! %s" % error)

    def _parse_model_list_string(self, model_list_string):
        lexer = get_model_list_lexer()
        parser = get_model_list_parser()
        try:
            return parser.parse(model_list_string, lexer=lexer)
        except ParserError as error:
            raise self.ParsingError("Invalid model list! %s" % error)
