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

import time
from logging import getLogger, INFO, WARNING, ERROR
from django.conf import settings
from django.contrib.auth import logout
#from django.contrib import messages
from .utils import AccessLoggerAdapter
from .models import Permission
from .settings import (
    ACCESS_LOGGER_NAME, DEFAULT_SESSION_IDLE_TIMEOUT,
)


def session_idle_timeout(get_response):

    def middleware(request):
        _logout_inactive(request)
        response = get_response(request)
        _update_timestamp(request)
        return response

    def _logout_inactive(request):
        if request.user.is_authenticated:
            try:
                last_activity = int(request.session[timestamp_tag])
            except (ValueError, TypeError, KeyError):
                last_activity = None
            if last_activity is None or (_now() - last_activity) > timeout:
                logout(request)
                #messages.error(request, "Session timed out.")

    def _update_timestamp(request):
        request.session[timestamp_tag] = _now()

    def _now():
        return int(time.time())

    timestamp_tag = 'timestamp'
    timeout = getattr(
        settings, 'SESSIONS_IDLE_TIMEOUT', DEFAULT_SESSION_IDLE_TIMEOUT
    )

    return middleware


def oauth_user_permissions_middleware(get_response):

    def middleware(request):
        request.user.oauth_user_permissions = (
            Permission.get_user_permissions(request.user)
            if request.user.is_authenticated else {}
        )
        return get_response(request)

    return middleware


def access_logging_middleware(get_response):
    logger = getLogger(ACCESS_LOGGER_NAME)

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
        response = get_response(request)
        is_authenticated = request.user.is_authenticated
        AccessLoggerAdapter(logger, request).log(
            get_log_level(response.status_code, is_authenticated),
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
