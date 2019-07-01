#-------------------------------------------------------------------------------
#
#  View decorators
#
# Authors: Martin Paces <martin.paces@eox.at>
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

from functools import wraps
from logging import getLogger, NOTSET
from django.http import HttpResponse
from django.shortcuts import redirect
from .settings import ACCESS_LOGGER_NAME

LOGGER = getLogger(ACCESS_LOGGER_NAME)


def log_access(level_authenticated=NOTSET, level_unauthenticated=NOTSET):
    """ Set the level for the request logging made by the access logging
    middleware.
    """
    def _decorator_(view_func):
        @wraps(view_func)
        def _wrapper_(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        _wrapper_.log_level_authenticated = level_authenticated
        _wrapper_.log_level_unauthenticated = level_unauthenticated
        return _wrapper_
    return _decorator_


def vires_admin_only(view_func):
    """ Allow only admin to access. """
    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if not request.user.is_vires_admin:
            return HttpResponse(
                'Not authorized!', content_type="text/plain", status=403
            )
        return view_func(request, *args, **kwargs)
    return _wrapper_


def reject_unauthenticated(view_func):
    """ Allow only authenticated users or deny access. """
    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse(
                'Authentication required!', content_type="text/plain", status=401
            )
        return view_func(request, *args, **kwargs)
    return _wrapper_


def redirect_unauthenticated(view_func):
    """ Allow only authenticated users or deny access. """
    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if not request.user.is_authenticated:
            response = redirect('account_login')
            response["Location"] += "?next=%s" % request.path
            return response
        return view_func(request, *args, **kwargs)
    return _wrapper_
