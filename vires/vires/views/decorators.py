#-------------------------------------------------------------------------------
#
# view decorators
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from logging import getLogger
from traceback import format_exc
from functools import wraps
from django.http import HttpResponse
from django.conf import settings
from ..util import format_exception
from .exceptions import HttpError


def set_extra_kwargs(**extra_kwargs):
    """ View decorator adding extra keyword arguments to the request. """
    def _set_extra_kwargs_(view):
        @wraps(view)
        def _set_extra_kwargs_wrapper_(request, *args, **kwargs):
            kwargs.update(extra_kwargs)
            return view(request, *args, **kwargs)
        return _set_extra_kwargs_wrapper_
    return _set_extra_kwargs_


def handle_error(view):
    """ error handling decorator """

    def _create_response(status, message, headers=None):
        response = HttpResponse(
            message, content_type="text/plain", status=status
        )
        for key, value in headers or []:
            response[key] = value
        return response

    @wraps(view)
    def _handle_error_(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except HttpError as error:
            return _create_response(error.status, str(error), error.headers)
        except Exception as error: # pylint: disable=broad-except
            logger = kwargs.get('logger') or getLogger(__name__)
            message = "Internal Server Error"
            logger.error("%s", format_exception())
            if settings.DEBUG:
                stack_trace = format_exc()
                # append stack trace to the message
                message = "%s\n\n%s" % (message, stack_trace)
                # log the stack-trace
                logger.debug("%s", stack_trace)
            return _create_response(500, message)
    return _handle_error_


def allow_methods(allowed_methods, allowed_headers=None, handle_options=True):
    """ Reject non-supported HTTP methods.
    By default the OPTIONS method is handled responding with
    the list of the supported methods and headers.
    """
    allowed_methods = set(allowed_methods)
    allowed_headers = list(allowed_headers or ["Content-Type"])
    if handle_options:
        allowed_methods.add('OPTIONS')

    def _allow_methods_decorator_(view):
        @wraps(view)
        def _allow_methods_(request, *args, **kwargs):
            if handle_options and request.method == "OPTIONS":
                response = HttpResponse(status=204)
                response['Access-Control-Allow-Methods'] = ", ".join(
                    allowed_methods
                )
                response['Access-Control-Allow-Headers'] = ", ".join(
                    allowed_headers
                )

            elif request.method not in allowed_methods:
                raise HttpError(
                    405, "Method not allowed",
                    headers=[('Allow', ', '.join(allowed_methods))]
                )
            else:
                response = view(request, *args, **kwargs)
            return response
        return _allow_methods_
    return _allow_methods_decorator_


def allow_content_types(content_types, methods=('POST', 'PUT')):
    """ Reject non-supported request content type.
    The content type is requested to be one of the listed.
    """
    methods = set(methods)
    content_types = set(content_types)

    def _allow_content_types_decorator_(view):
        @wraps(view)
        def _allow_content_types_(request, *args, **kwargs):
            if request.method in methods:
                content_type = request.META.get("CONTENT_TYPE")
                if content_type not in content_types:
                    if content_type is None:
                        raise HttpError(
                            400, "Missing mandatory payload content type!"
                        )
                    else:
                        raise HttpError(
                            400, "Invalid payload content type!"
                        )
            return view(request, *args, **kwargs)
        return _allow_content_types_
    return _allow_content_types_decorator_


def allow_content_length(max_content_length, methods=('POST', 'PUT')):
    """ Reject requests exceeding the allowed content length. """
    methods = set(methods)
    def _allow_content_length_decorator_(view):
        @wraps(view)
        def _allow_content_length_(request, *args, **kwargs):
            content_length = int(request.META.get("CONTENT_LENGTH", 0))
            if request.method in methods:
                if content_length > max_content_length:
                    raise HttpError(413, "Payload too large!")
            elif content_length > 0:
                raise HttpError(400, "Payload not allowed!")
            return view(request, *args, **kwargs)
        return _allow_content_length_
    return _allow_content_length_decorator_


def reject_content(view):
    """ Reject requests containing content. """
    @wraps(view)
    def _no_content_(request, *args, **kwargs):
        content_length = int(request.META.get("CONTENT_LENGTH", 0))
        if content_length > 0:
            raise HttpError(400, "Payload not allowed!")
        return view(request, *args, **kwargs)
    return _no_content_
