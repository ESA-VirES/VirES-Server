#-------------------------------------------------------------------------------
#
# VirES HAPI - views - common utilities
#
# https://github.com/hapi-server/data-specification/blob/master/hapi-3.0.0/HAPI-data-access-spec-3.0.0.md
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
# pylint: disable=missing-docstring,too-few-public-methods

from logging import getLogger
from traceback import format_exc
from datetime import datetime, time
from django.utils.dateparse import (
    parse_date as django_parse_date,
    parse_datetime as django_parse_datetime,
)
from django.http import JsonResponse
from django.conf import settings
from vires.views.exceptions import HttpError
from vires.time_util import naive_to_utc

LOGGER_NAME = "vires.hapi"


class HapiResponse(JsonResponse):
    """ HAPI HTTP response class. """

    VERSION = "3.0"
    STATUS_CODES = {
        1200: (200, "OK"),
        1201: (200, "OK - no data for time range"),
        1400: (400, "Bad request - user input error"),
        1401: (400, "Bad request - unknown API parameter name"),
        1402: (400, "Bad request - error in start time"),
        1403: (400, "Bad request - error in stop time"),
        1404: (400, "Bad request - start time equal to or after stop time"),
        1405: (400, "Bad request - time outside valid range"),
        1406: (404, "Bad request - unknown dataset id"),
        1407: (404, "Bad request - unknown dataset parameter"),
        1408: (400, "Bad request - too much time or data requested"),
        1409: (400, "Bad request - unsupported output format"),
        1410: (400, "Bad request - unsupported include value"),
        1500: (500, "Internal server error"),
        1501: (500, "Internal server error - upstream request error"),
    }

    @classmethod
    def generate_status(cls, code, message, debug=None):
        """ Generate status record. """
        status = {
            "code": code,
            "message": message or 'Request error',
        }
        if debug:
            # optional debugging message - not part of the HAPI spec
            status["x_debug"] = debug
        return status

    def __init__(self, content=None, hapi_status=1200, http_status=None,
                 message=None, debug=None, **kwargs):
        if http_status is None:
            #  HAPI errors
            http_status, default_message = self.STATUS_CODES[hapi_status]
            message = (
                f"{default_message} - {message}" if message else default_message
            )
        else:
            hapi_status = 1400

        super().__init__({
            "HAPI": self.VERSION,
            "status": self.generate_status(hapi_status, message, debug),
            **(content or {}),
        }, status=http_status, **kwargs)


class HapiError(Exception):
    """ HAPI error exception. """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.response = HapiResponse(*args, **kwargs)


def catch_error(view):
    """ Decorator catching internal errors and returning HAPI 1500 error. """
    def _catch_error(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except HapiError as error:
            return error.response
        except HttpError as error:
            return HapiResponse(http_status=error.status, message=str(error))
        except Exception as error:
            getLogger(LOGGER_NAME).error("Internal serve error!", exc_info=True)
            return HapiResponse(
                hapi_status=1500, message=str(error),
                debug=(format_exc() if settings.DEBUG else None),
            )
    return _catch_error


def allowed_parameters(*allowed_parameters):
    """ Decorator checking the HAPI request allowed parameters. """
    allowed_parameters = set(allowed_parameters)
    def check_allowed_parameters(view):
        def _check_allowed_parameters(request, *args, **kwargs):
            extra_parameters = set(request.GET.keys()) - allowed_parameters
            if extra_parameters:
                raise HapiError(hapi_status=1401, message=(
                    f"unexpected request parameter '{next(iter(extra_parameters))}'"
                ))
            return view(request, *args, **kwargs)
        return _check_allowed_parameters
    return check_allowed_parameters


def map_parameters(*parameters_mapping):
    """ Decorator mapping alternative request parameters to their target
    destination. The target parameters and their optional alternatives
    are mutually exclusive.
    This decorator is meant to handle backward compatibility for the renamed
    request parameters.
    """
    def map_parameter_names(view):
        def _map_parameter_names(request, *args, **kwargs):
            is_copy = False
            for target, alternative in parameters_mapping:
                if alternative in request.GET:
                    if target in request.GET:
                        raise HapiError(hapi_status=1400, message=(
                            f"'{target}' and '{alternative}' parameters cannot be "
                            "present simultaneously"
                        ))
                    if not is_copy:
                        request.GET = request.GET.copy()
                        is_copy = True
                    request.GET.setlist(target, request.GET.pop(alternative))
            return view(request, *args, **kwargs)
        return _map_parameter_names
    return map_parameter_names


def required_parameters(*required_parameters):
    """ Decorator checking the HAPI request required parameters. """
    required_parameters = set(required_parameters)
    def check_required_parameters(view):
        def _check_required_parameters(request, *args, **kwargs):
            missing_parameters = required_parameters - set(request.GET.keys())
            if missing_parameters:
                raise HapiError(hapi_status=1400, message=(
                    f"missing mandatory request parameter '{next(iter(missing_parameters))}'"
                ))
            return view(request, *args, **kwargs)
        return _check_required_parameters
    return check_required_parameters


def parse_datetime(value):
    """ Parse date-time value. """
    parsed_value = django_parse_datetime(value)
    if parsed_value is not None:
        return naive_to_utc(parsed_value)
    parsed_value = django_parse_date(value)
    if parsed_value is not None:
        return naive_to_utc(datetime.combine(parsed_value, time()))
    raise ValueError(f"invalid time {value}'")
