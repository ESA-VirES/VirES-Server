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

#from logging import getLogger
from vires.views.decorators import allow_methods, reject_content
from vires.time_util import format_datetime
from ..dataset import MAX_TIME_SELECTION, get_time_limit, get_collection_time_info
from ..time_series import TimeSeries
from .common import (
    parse_datetime, HapiError, get_access_logger,
    catch_error, allowed_parameters, required_parameters, map_parameters,
)
from .data_formats import get_data_formatter, parse_format
from .info import get_info_response, parse_dataset_and_parameters

#LOGGER_NAME = "vires.hapi"


@catch_error
@allow_methods(['GET'])
@reject_content
@allowed_parameters(
    "dataset", "id", "start", "time.min", "stop", "time.max", "parameters",
    "include", "format"
)
@map_parameters(("dataset", "id"), ("start", "time.min"), ("stop", "time.max"))
@required_parameters("dataset", "start", "stop")
def data(request):

    access_logger = get_access_logger("data", request)

    collection, dataset_id, dataset_def, options = parse_dataset_and_parameters(
        request.GET.get('dataset'), request.GET.get('parameters')
    )

    start, stop = _parse_time_selection(
        collection, request.GET.get('start'), request.GET.get('stop')
    )

    format_ = _parse_format(request.GET.get('format'))

    include_header = _parse_header_flag(request.GET.get('include'))

    source = TimeSeries(collection, dataset_id, options)

    # log the request
    access_logger.info(
        "request: dataset: %s, toi: (%s, %s), parameters: (%s), format: %s",
        request.GET.get('dataset'),
        format_datetime(start),
        format_datetime(stop),
        ", ".join(dataset_def.keys()),
        request.GET.get('format'),
    )

    return get_data_formatter(format_)(
        datasets=source.subset(start, stop, dataset_def),
        header=(
            get_info_response(collection, dataset_id, dataset_def, options)
            if include_header else None
        ),
        logger=access_logger,
    )


def _parse_time_selection(collection, start, stop):

    try:
        start = parse_datetime(start)
    except ValueError:
        raise HapiError(hapi_status=1402) from None

    try:
        stop = parse_datetime(stop)
    except ValueError:
        raise HapiError(hapi_status=1403) from None

    if start >= stop:
        raise HapiError(hapi_status=1404)

    time_info = get_collection_time_info(collection)

    data_start, data_stop = time_info["startDate"], time_info["stopDate"]
    no_data = data_start is None and data_stop is None
    if no_data or start < data_start or stop > data_stop:
        raise HapiError(hapi_status=1405) from None

    if stop - start > get_time_limit(MAX_TIME_SELECTION, time_info["cadence"]):
        raise HapiError(hapi_status=1408) from None

    return start, stop


def _parse_format(format_):
    try:
        return parse_format(format_)
    except ValueError:
        raise HapiError(hapi_status=1409) from None


def _parse_header_flag(header_flag):
    if header_flag is None:
        return False
    if header_flag == 'header':
        return True
    raise HapiError(hapi_status=1410) from None
