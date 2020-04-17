#-------------------------------------------------------------------------------
#
#  VirES for Swarm specific - WMS input parsers
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments,too-many-boolean-expressions,too-many-locals

from eoxserver.core.decoders import InvalidParameterException
from vires.processes.util import parse_model_list, ALLOWED_VARIABLES


SUPPORTED_SRIDS = (4326,)
SUPPORTED_FORMATS = ("image/png",)
MAX_IMAGE_SIZE = (2048, 2048)


def get_mean_time(time):
    """ Extract single (mean) time from the time selection. """
    if time is None:
        return None
    if hasattr(time, "__len__"):
        if len(time) == 2:
            return (time[1] - time[0]) / 2 + time[0]
        if len(time) == 1:
            return time[0]
    raise ValueError("Invalid time selection! %s" % time)


def get_models(query, layers):
    """ Extract and parse models from the query dict. """
    model_list_string = parse_query_parameter(
        query, "models", lambda s: s.strip(), default=[""]
    )
    if model_list_string:
        model_list_string += "," + ",".join(layers)
    else:
        model_list_string = ",".join(layers)

    models, _ = parse_model_list("models", model_list_string)
    return models


def parse_query_parameter(query, parameter, parser, default=None,
                          multiple_values=False):
    """ Parse parameter from the query dictionary. """
    input_ = query.get(parameter, default)
    if input_ is not None and not multiple_values:
        if len(input_) == 1:
            input_ = input_[0]
        elif len(input_) > 1:
            raise InvalidParameterException(
                "Unexpected multiple values of %r parameter!" % parameter,
                parameter
            )
        else:
            input_ = None

    if input_ is None:
        raise InvalidParameterException(
            "Missing mandatory %r parameter!" % parameter, parameter
        )

    try:
        if multiple_values:
            result = [parser(item) for item in input_]
        else:
            result = parser(input_)
    except (TypeError, ValueError) as error:
        raise InvalidParameterException(str(error), parameter)

    return result


def parse_colormaps(input_string):
    """ Parse colormap ids. """
    return [v.strip() for v in input_string.split(',')]


def parse_value_range(input_string):
    """ parse value range """
    min_value, max_value = [float(v) for v in input_string.split(',')]
    return (min_value, max_value)


def parse_variable(input_string):
    """ parse variable """
    variable, = [v.strip() for v in input_string.split(',')]
    if variable not in ALLOWED_VARIABLES:
        raise ValueError("Invalid variable!")
    return variable


def parse_bool(input_string):
    """ Parse boolean value. """
    return input_string.strip().lower() == "true"
