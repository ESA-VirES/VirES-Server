#-------------------------------------------------------------------------------
#
#  Auxiliary middle-ware classes
#
# Project: EOxServer - django-allauth integration.
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
# pylint: disable=missing-docstring, no-self-use, unused-argument

from logging import getLogger, INFO, WARNING, ERROR
from django.contrib.auth import logout
from .utils import AccessLoggerAdapter, get_remote_addr, get_username

ACCESS_LOGGER_NAME = "access.http"


def access_logging_middleware(get_response):
    base_logger = getLogger(ACCESS_LOGGER_NAME)

    # log levels are set via the  `log_access` decorator
    log_level_authenticated = getattr(
        get_response, 'log_level_authenticated', INFO
    )
    log_level_unauthenticated = getattr(
        get_response, 'log_level_unauthenticated', INFO
    )

    def get_log_level(status_code, is_authenticated):
        if status_code < 400:
            if is_authenticated:
                return log_level_authenticated
            return log_level_unauthenticated
        if status_code < 500:
            return WARNING
        return ERROR

    def middleware(request):
        remote_addr = get_remote_addr(request)

        # Extract username if the user has been already authenticated.
        username = get_username(request.user)

        response = get_response(request)

        # Update username if the authentication happened later
        # in the middleware/decorator chain.
        # Note that the username extraction after calling the request handler
        # does not extract username for the logout requests.
        username = username or get_username(request.user)

        AccessLoggerAdapter(
            logger=base_logger, username=username, remote_addr=remote_addr
        ).log(
            get_log_level(response.status_code, request.user.is_authenticated),
            "%s %s %s %s ", request.method, request.path, response.status_code,
            response.reason_phrase,
        )

        return response

    return middleware


def inactive_user_logout_middleware(get_response):

    def middleware(request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
        return get_response(request)

    return middleware
