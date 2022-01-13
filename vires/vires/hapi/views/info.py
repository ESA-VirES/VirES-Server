#-------------------------------------------------------------------------------
#
# VirES HAPI 3.0.0 views
#
# https://github.com/hapi-server/data-specification/blob/master/hapi-3.0.0/HAPI-data-access-spec-3.0.0.md
#
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,unused-argument,too-few-public-methods

from django.db.models import Min, Max
from vires.time_util import format_datetime#, parse_duration
from vires.views.decorators import allow_methods, reject_content
from ..dataset import parse_dataset
from ..formats.common import get_datetime64_string_size
from ..data_type import parse_data_type
from .common import (
    HapiResponse, HapiError,
    catch_error, allowed_parameters, required_parameters, map_parameters
)


@catch_error
@allow_methods(['GET'])
@reject_content
@allowed_parameters("dataset", "id", "parameters")
@map_parameters(("dataset", "id"))
@required_parameters("dataset")
def info(request):
    collection, dataset_id, dataset_def = parse_dataset_and_parameters(
        request.GET.get('dataset'), request.GET.get('parameters')
    )
    return HapiResponse(get_info_response(collection, dataset_id, dataset_def))


def parse_dataset_and_parameters(hapi_dataset_id, parameters):
    """ Parse dataset id and the requested parameters. """
    try:
        collection, dataset_id, dataset_def = parse_dataset(hapi_dataset_id)
    except (KeyError, ValueError):
        raise HapiError(hapi_status=1406) from None
    try:
        dataset_def = _parse_parameters(parameters, dataset_def)
    except ValueError as error:
        raise HapiError(hapi_status=1407, message=str(error)) from None
    return collection, dataset_id, dataset_def


def get_info_response(collection, dataset_id, dataset_def):
    """ Build info response. """

    metadata = {
        **collection.metadata,
        **collection.products.aggregate(
            startDate=Min("begin_time"),
            stopDate=Max("end_time"),
            lastUpdate=Max("updated"),
        )
    }

    return {
        "x_dataset": collection.identifier + (
            f":{dataset_id}" if dataset_id else ""
        ),
        "x_datasetType": collection.type.identifier + (
            f":{dataset_id}" if dataset_id else ""
        ),
        "startDate": format_datetime(metadata["startDate"]),
        "stopDate": format_datetime(metadata["stopDate"]),
        "cadence": metadata.get("nominalSampling"),
        "modificationDate": metadata.get("lastUpdate"),
        "parameters": [
            _build_parameter(name, details)
            for name, details in dataset_def.items()
        ],
    }


def sort_dataset_definition(definition):
    """ Sort dataset definitions according to the order index. """
    return dict(sorted(
        definition.items(), key=lambda item: item[1].get("_order") or 0
    ))


def _parse_parameters(requested_parameters, dataset_definition):
    """ parse parameter list and return applicable subset of the
    dataset definition.
    """
    def _find_duplicates(items):
        observed = set()
        for item in items:
            if item in observed:
                yield item
            else:
                observed.add(item)

    def _extract_definitions(parameters_it, definition):
        """ Extract definitions for the selected parameters and check the
        order of the requested parameters.
        Note that the primary time parameter is always included in the result
        even if not explicitly included in the request.
        """
        try:
            requested_parameter = next(parameters_it)
        except StopIteration:
            return

        for parameter, parameter_def in definition.items():
            if parameter == requested_parameter:
                yield parameter, parameter_def
                try:
                    requested_parameter = next(parameters_it)
                except StopIteration:
                    break
            elif parameter_def.get('primaryTimestamp'):
                yield parameter, parameter_def
        else:
            raise ValueError(
                f"unexpected position of {requested_parameter} parameter"
            )

    def _parse_requested_parameters(parameters, definition):
        if not requested_parameters.strip():
            raise ValueError("blank parameter list")
        parameters = parameters.split(',')
        parameters_set = set(parameters)

        for parameter in parameters_set - set(definition):
            raise ValueError(f"invalid parameter {parameter}")

        if len(parameters_set) < len(parameters):
            for parameter in _find_duplicates(parameters):
                raise ValueError(f"duplicate parameter '{parameter}'")

        return dict(_extract_definitions(iter(parameters), definition))


    dataset_definition = sort_dataset_definition(dataset_definition)

    if not requested_parameters:
        return dataset_definition

    return _parse_requested_parameters(requested_parameters, dataset_definition)



def _build_parameter(name, details):
    """ Build parameter object. """

    def _parse_dimension(dimension):
        if dimension is None:
            return {}
        return {"size": dimension}

    def _parse_unit(unit):
        if unit is None or unit.strip() in ("", "-"):
            return None
        return unit

    return {
        "name": name,
        **_HapiDataType(details),
        **_parse_dimension(details.get("dimension")),
        "units": _parse_unit(details["attributes"].get("UNITS")),
        "description": (details["attributes"].get("DESCRIPTION") or ""),
        "fill": details.get("nodataValue"),
    }


class _HapiDataType():
    """ HAPI data-type description factory. """

    NUMBER_TYPE_MAPPING = {
        "float": "double",
        "uint": "integer",
        "int": "integer",
    }

    NUMBER_TYPE_SIZES = {
        "uint": (8, 16, 32, 64),
        "int": (8, 16, 32, 64),
        "float": (32, 64),
    }

    def __new__(cls, vires_parameter):
        data_type = parse_data_type(vires_parameter)

        if data_type.type in ('float', 'int', 'uint'):
            return {
                "type": cls.NUMBER_TYPE_MAPPING[data_type.type],
                "x_type": data_type.type_string,
            }

        if data_type.type == "timestamp":
            return {
                "type": "isotime",
                "length": get_datetime64_string_size(data_type.dtype),
                "x_standard": data_type.standard,
                "x_epoch": data_type.epoch,
                "x_unit": data_type.unit,
                "x_type": data_type.storage_type,
            }

        if data_type.type in ('char', 'unicode'):
            return {
                "type": "string",
                "length": data_type.byte_size,
                "x_encoding": data_type.encoding,
            }

        raise ValueError(f"Unsupported data type {data_type.type}!")
