#-------------------------------------------------------------------------------
#
# Process Utilities - Input Parsers
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=missing-docstring,import-error
import re
from collections import OrderedDict
from eoxmagmod import load_model_shc
from eoxserver.services.ows.wps.exceptions import (
    MissingRequiredInputError, InvalidInputValueError
)
from vires.util import get_color_scale
from vires.models import ProductCollection
from vires.parsers.exceptions import ParserError
from vires.parsers.model_list_parser import get_model_list_parser
from vires.parsers.model_list_lexer import get_model_list_lexer
from vires.parsers.model_expression_parser import get_model_expression_parser
from vires.parsers.model_expression_lexer import get_model_expression_lexer
from .time_series_product import ProductTimeSeries
from .model_magmod import SourceMagneticModel, ComposedMagneticModel
from .filters import ScalarRangeFilter, VectorComponentRangeFilter
from .magnetic_models import get_model


RE_FILTER_NAME = re.compile(r'(^[^[]+)(?:\[([0-9])\])?$')
RE_RESIDUAL_VARIABLE = re.compile(r'(.+)_res([ABC])([ABC])')


def parse_style(input_id, style):
    """ Parse style value and return the corresponding colour-map object. """
    if style is None:
        return None
    try:
        return get_color_scale(style)
    except ValueError:
        raise InvalidInputValueError(
            input_id, "Invalid style identifier %r!" % style
        )


def parse_collections(input_id, source):
    """ Parse input collections definitions. """
    result = {}
    if not isinstance(source, dict):
        raise InvalidInputValueError(
            input_id, "JSON object expected!"
        )
    # resolve collection ids
    for label, collection_ids in source.iteritems():
        if not isinstance(collection_ids, (list, tuple)):
            raise InvalidInputValueError(
                input_id, "A list of collection identifiers expected for "
                "label %r!" % label
            )
        available_collections = dict(
            (obj.identifier, obj) for obj in ProductCollection.objects.filter(
                identifier__in=collection_ids
            )
        )
        try:
            result[label] = [
                available_collections[id_] for id_ in collection_ids
            ]
        except KeyError as exc:
            raise InvalidInputValueError(
                input_id, "Invalid collection identifier %r! (label: %r)" %
                (exc.args[0], label)
            )

    range_types = []
    master_rtype = None
    for label, collections in result.items():
        # master (first collection) must be always defined
        if len(collections) < 1:
            raise InvalidInputValueError(
                input_id, "Collection list must have at least one item!"
                " (label: %r)" % label
            )
        # master (first collection) must be always of the same range-type
        if master_rtype is None:
            master_rtype = collections[0].range_type
            range_types = [master_rtype] # master is always the first
        else:
            if master_rtype != collections[0].range_type:
                raise InvalidInputValueError(
                    input_id, "Master collection type mismatch!"
                    " (label: %r; )" % label
                )

        # slaves are optional
        # slaves' order does not matter

        # collect slave range-types
        slave_rtypes = []

        # for one label multiple collections of the same renge-type not allowed
        for rtype in (collection.range_type for collection in collections[1:]):
            if rtype == master_rtype or rtype in slave_rtypes:
                raise InvalidInputValueError(
                    input_id, "Multiple collections of the same type "
                    "are not allowed! (label: %r; )" % label
                )
            slave_rtypes.append(rtype)

        # collect all unique range-types
        range_types.extend(
            rtype for rtype in slave_rtypes if rtype not in range_types
        )

    # convert collections to product time-series
    return dict(
        (label, [ProductTimeSeries(collection) for collection in collections])
        for label, collections in result.iteritems()
    )


def parse_model_expression(input_id, model_input, shc, shc_input_id="shc"):
    """ Parse model expression and returns the final composed model and
    a list of model sources.
    """
    known_models, source_models = {}, {}

    custom_model = _parse_custom_model(shc_input_id, shc)
    if custom_model is not None:
        known_models[custom_model.name] = custom_model

    model_obj = ComposedMagneticModel("<nameless>", [
        _process_model_component(
            known_models, source_models, component, input_id
        ) for component in _parse_model_expression_string(input_id, model_input)
    ])

    return model_obj, source_models.values()


def _parse_model_expression_string(input_id, model_expression_string):
    lexer = get_model_expression_lexer()
    parser = get_model_expression_parser()
    try:
        return parser.parse(model_expression_string, lexer=lexer)
    except ParserError as error:
        raise InvalidInputValueError(
            input_id, "Invalid model expression! %s" % error
        )


def parse_model_list(input_id, models_input, shc, shc_input_id="shc"):
    """ Parse list of model and return a list of named composed models and
    source models.
    """
    requested_models, known_models, source_models = [], {}, {}

    custom_model = _parse_custom_model(shc_input_id, shc)
    if custom_model is not None:
        known_models[custom_model.name] = custom_model

    for model_def in _parse_model_list_string(input_id, models_input):
        requested_models.append(_process_composed_model(
            known_models, source_models, model_def, input_id
        ))

    return requested_models, source_models.values()


def _parse_model_list_string(input_id, model_list_string):
    lexer = get_model_list_lexer()
    parser = get_model_list_parser()
    try:
        return parser.parse(model_list_string, lexer=lexer)
    except ParserError as error:
        raise InvalidInputValueError(
            input_id, "Invalid model list! %s" % error
        )


def _parse_custom_model(input_id, shc_coefficients):
    if shc_coefficients is None:
        return None
    try:
        model = load_model_shc(shc_coefficients)
    except ValueError:
        raise InvalidInputValueError(
            input_id, "Failed to parse the custom model coefficients."
        )
    return ComposedMagneticModel("Custom_Model", [
        (1.0, SourceMagneticModel(
            "Custom_Model", model, {"min_degree": 0, "max_degree": model.degree}
        ))
    ])


def _process_composed_model(known_models, source_models, model_def, input_id):
    model_obj = ComposedMagneticModel(model_def.id, [
        _process_model_component(
            known_models, source_models, component, input_id
        ) for component in model_def.components
    ])
    known_models[model_def.id] = model_obj
    return model_obj


def _process_model_component(known_models, source_models, model_def, input_id):

    def _get_degree_range(parameters, min_degree, max_degree):
        _max_degree = min(parameters.get("max_degree", max_degree), max_degree)
        max_degree = max_degree if _max_degree < 0 else _max_degree
        min_degree = max(parameters.get("min_degree", min_degree), min_degree)
        return {"min_degree": min_degree, "max_degree": max_degree}

    def _create_source_model(model_id, model, params):
        model_obj = SourceMagneticModel(model_id, model, params)
        source_models[model_obj.name] = model_obj
        return model_obj

    model_id = model_def.id
    parameters = model_def.parameters.copy()
    scale = parameters.pop("scale", 1)

    model_obj = known_models.get(model_id)
    if model_obj is not None:
        if (
                isinstance(model_obj, ComposedMagneticModel) and
                len(model_obj.components) == 1
            ):
            model_scale, model_obj = model_obj.components[0]
            scale *= model_scale

        if isinstance(model_obj, SourceMagneticModel):
            model_obj = _create_source_model(
                model_id, model_obj.model, _get_degree_range(
                    parameters, **model_obj.parameters
                )
            )
        else:
            for parameter in parameters:
                raise InvalidInputValueError(input_id, (
                    "The %s parameter is not allowed for a non-source model %s!"
                    % (parameter, model_id)
                ))
    else: # new source model
        model = get_model(model_def.id)
        if model is None:
            raise InvalidInputValueError(
                input_id, "Invalid model identifier %r!" % model_def.id
            )
        model_obj = _create_source_model(
            model_id, model, _get_degree_range(parameters, 0, model.degree)
        )

    return scale, model_obj


def parse_filters(input_id, filter_string):
    """ Parse filters' string. """
    try:
        filters = OrderedDict()
        if filter_string.strip():
            for item in filter_string.split(";"):
                name, bounds = item.split(":")
                name = name.strip()
                if not name:
                    raise ValueError("Invalid empty filter name!")
                lower, upper = [float(v) for v in bounds.split(",")]
                if name in filters:
                    raise ValueError("Duplicate filter %r!" % name)
                filters[name] = (lower, upper)
    except ValueError as exc:
        raise InvalidInputValueError(input_id, exc)
    return filters


def parse_filters2(input_id, filter_string):
    """ Parse filters' string and return list of the filter objects. """

    def _get_filter(name, vmin, vmax):
        match = RE_FILTER_NAME.match(name)
        if match is None:
            raise InvalidInputValueError(
                input_id, "Invalid filter name %r" % name
            )
        variable, component = match.groups()
        if component is None:
            return ScalarRangeFilter(variable, vmin, vmax)
        else:
            return VectorComponentRangeFilter(
                variable, int(component), vmin, vmax
            )

    return [
        _get_filter(name, vmin, vmax) for name, (vmin, vmax)
        in parse_filters(input_id, filter_string).iteritems()
    ]


def parse_variables(input_id, variables_strings):
    """ Variable parsers.  """
    variables_strings = str(variables_strings.strip())
    return [
        var.strip() for var in variables_strings.split(',')
    ] if variables_strings else []


def get_residual_variables(variables):
    """ Extract residual variables from a list of all variables. """
    return [
        (variable, match.groups()) for variable, match in (
            (var, RE_RESIDUAL_VARIABLE.match(var)) for var in variables
        ) if match
    ]
