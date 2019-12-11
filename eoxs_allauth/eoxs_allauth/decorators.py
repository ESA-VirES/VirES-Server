#-------------------------------------------------------------------------------
#
#  Auxiliary views decorators.
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
# pylint: disable=missing-docstring

import re
from functools import wraps
from logging import getLogger, NOTSET
from django.utils.timezone import now
from django.core.exceptions import PermissionDenied
from .models import AuthenticationToken

LOGGER = getLogger("eoxs_allauth.access")


def log_access(level_authenticated=NOTSET, level_unauthenticated=NOTSET):
    """ Set the level for the request logging made by the access logging
    middleware.
    """
    def _decorator_(view_func):
        view_func.log_level_authenticated = level_authenticated
        view_func.log_level_unauthenticated = level_unauthenticated
        return view_func
    return _decorator_


def authenticated_only(view_func):
    """ Allow only authenticated users or deny access. """
    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapper_


def token_authentication(view_func):
    """ Perform access token authentication. """
    # NOTE: Make sure the HTTP server is configured so that the Authorization
    #       header is passed to the WSGI interface (WSGIPassAuthorization On).
    re_bearer = re.compile(r"^Bearer (?P<token>[a-zA-Z0-9_-]{32,32})$")

    def _extract_token(request):
        match = re_bearer.match(request.META.get("HTTP_AUTHORIZATION", ""))
        return match.groupdict()['token'] if match else None

    def _get_user(token):
        if not token:
            return None
        try:
            model = (
                AuthenticationToken.objects
                .select_related('owner')
                .get(token=token)
            )
        except AuthenticationToken.DoesNotExist:
            return None

        if model.expires and model.expires <= now(): # check for expired token
            model.delete()
            return None

        return model.owner

    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if not request.user.is_authenticated:
            user = _get_user(_extract_token(request))
            if user and user.is_active:
                request.user = user
        return view_func(request, *args, **kwargs)
    return _wrapper_
