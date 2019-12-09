#-------------------------------------------------------------------------------
#
#  VirES specific view decorators.
#
# Project: EOxServer - django-allauth integration.
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
# pylint: disable=missing-docstring

from functools import wraps
from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from .permissions import get_user_permissions, get_required_permission
from .messages import add_message_access_denied


def authorized_only(view_func):
    """ Allow only authorized users or return 403 response. """

    def _reject_unauthorized_view(*args, **kwargs):
        raise PermissionDenied

    return _check_vires_authorization(view_func, _reject_unauthorized_view)


def logout_unauthorized(view_func):
    """ Log out unauthorized users. """

    def _logout_unauthorized_view(request, *args, **kwargs):
        if request.user.is_authenticated():
            logout(request)
            add_message_access_denied(request)
        return view_func(request, *args, **kwargs)

    return _check_vires_authorization(view_func, _logout_unauthorized_view)


def redirect_unauthorized(redirect_url):
    """ Log out and redirect unauthorized users. """

    def _redirect_unauthorized(view_func):

        def _redirect_unauthorized_view(request, *args, **kwargs):
            if request.user.is_authenticated():
                logout(request)
                add_message_access_denied(request)
            return HttpResponseRedirect(redirect_url)

        return _check_vires_authorization(view_func, _redirect_unauthorized_view)

    return _redirect_unauthorized


def _check_vires_authorization(handle_authorized, handle_unauthorized):
    """ Low level VirES access authorization. """
    required_permission = get_required_permission()

    @wraps(handle_authorized)
    def _wrapper_(request, *args, **kwargs):
        user = request.user
        granted_permissions = get_user_permissions(user)
        user_is_authorized = (
            not required_permission or required_permission in granted_permissions
        )
        user.is_authorized = user_is_authorized
        user.vires_permissions = granted_permissions
        return (
            handle_authorized if user_is_authorized else handle_unauthorized
        )(request, *args, **kwargs)

    return _wrapper_
