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
from collections import OrderedDict
from eoxmagmod import read_model_shc
from eoxserver.contrib import gdal
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.util import get_color_scale, get_model
from vires.models import ProductCollection
from .time_series_product import ProductTimeSeries
from .model_magmod import MagneticModel

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
    # check the collection counts and range types
    if result:
        labels = iter(result)
        label = labels.next()
        collections = result[label]
        count = len(collections)
        rtypes = tuple(col.range_type for col in collections)
        if len(set(rtypes)) < len(rtypes):
            raise InvalidInputValueError(
                input_id, "Non-unique collection range-types! (label: %r; )" %
                label
            )
        for label in labels:
            collections = result[label]
            # check count
            if len(collections) != count:
                raise InvalidInputValueError(
                    input_id, "Collection count mismatch! (label: %r; )" %
                    label
                )
            # check range types
            if tuple(col.range_type for col in collections) != rtypes:
                raise InvalidInputValueError(
                    input_id, "Collection range-type mismatch! (label: %r; )" %
                    label
                )
    # convert collections to product time-series
    return dict(
        (label, [ProductTimeSeries(collection) for collection in collections])
        for label, collections in result.iteritems()
    )


def parse_model(input_id, model_id, shc, shc_input_id="shc"):
    """ Parse model identifier and returns the corresponding model."""
    if model_id == "Custom_Model":
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
    the corresponding models.
    """
    models = OrderedDict()
    if model_ids.strip():
        for model_id in (id_.strip() for id_ in model_ids.split(",")):
            models[model_id] = parse_model(
                input_id, model_id, shc, shc_input_id
            )
    return models


def parse_models2(input_id, model_ids, shc, shc_input_id="shc"):
    """ Parse model identifiers and returns an ordered dictionary
    the corresponding models.
    """
    models = parse_models(input_id, model_ids, shc, shc_input_id)
    return [MagneticModel(id_, model) for id_, model in models.iteritems()]


def parse_filters(input_id, filter_string):
    """ Parse filters' string. """
    try:
        filter_ = OrderedDict()
        if filter_string.strip():
            for item in filter_string.split(";"):
                name, bounds = item.split(":")
                name = name.strip()
                if not name:
                    raise ValueError("Invalid empty filter name!")
                lower, upper = [float(v) for v in bounds.split(",")]
                filter_[name] = (lower, upper)
    except ValueError as exc:
        raise InvalidInputValueError(input_id, exc)
    return filter_
