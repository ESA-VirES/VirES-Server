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
from logging import NOTSET
from urllib.parse import quote
import json
import base64
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from oauth2_provider.settings import oauth2_settings
from .altcha import (
    AltchaError, is_altcha_enabled, verify_solved_altcha_challange,
)


def altcha_verify(view_func):
    """ Verify solved Altcha challenge. """

    def _parse_altcha_payload(raw_payload):
        return json.loads(base64.b64decode(raw_payload).decode("UTF-8"))

    def _verify_altcha(request):

        if request.method == "POST" and is_altcha_enabled():

            try:
                payload = _parse_altcha_payload(request.POST["altcha"])
            except:
                return False

            try:
                return verify_solved_altcha_challange(payload)
            except AltchaError:
                return False

        return True

    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if _verify_altcha(request):
            return view_func(request, *args, **kwargs)
        return HttpResponse('Not authorized!', content_type="text/plain", status=403)

    return _wrapper_


def oauth2_protected(*required_scopes):
    """ View decorator performing OAuth2 authentication and scope
    authorization.
    """
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS
    def _decorator_(view_func):
        @wraps(view_func)
        def _wrapper_(request, *args, **kwargs):
            core = oauthlib_backend_class(server_class(validator_class()))
            is_valid, oauthlib_req = core.verify_request(
                request, scopes=required_scopes
            )
            if not is_valid or not oauthlib_req.user.is_active:
                return HttpResponse(
                    'Not authorized!', content_type="text/plain", status=403
                )
            request.user = oauthlib_req.user
            request.access_token = oauthlib_req.access_token
            request.client = oauthlib_req.client
            return view_func(request, *args, **kwargs)
        return _wrapper_
    return _decorator_


def log_access(level_authenticated=NOTSET, level_unauthenticated=NOTSET):
    """ Set the level for the request logging made by the access logging
    middleware.
    """
    def _decorator_(view_func):
        view_func.log_level_authenticated = level_authenticated
        view_func.log_level_unauthenticated = level_unauthenticated
        return view_func
    return _decorator_


def has_permission(*permissions):
    """ Authorize if the user has one of the required permissions. """
    def _has_oauth_user_permission_(view_func):
        @wraps(view_func)
        def _wrapper_(request, *args, **kwargs):
            user_permissions = request.user.oauth_user_permissions
            for permission in permissions:
                if permission in user_permissions:
                    break
            else:
                return HttpResponse(
                    'Not authorized!', content_type="text/plain", status=403
                )
            return view_func(request, *args, **kwargs)
        return _wrapper_
    return _has_oauth_user_permission_


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
            response["Location"] += "?next=%s" % quote(request.get_full_path())
            return response
        return view_func(request, *args, **kwargs)
    return _wrapper_


def log_exception(logger):
    """ Log any exception raised from the wrapped view. """
    def _decorator_(view_func):
        @wraps(view_func)
        def _wrapper_(*args, **kwargs):
            try:
                return view_func(*args, **kwargs)
            except Exception as error:
                logger.error("%s: %s", view_func.__name__, error)
                raise
        return _wrapper_
    return _decorator_


def request_consent(view_func):
    """ Request legal consent with the current service terms and related
    documents. """
    required_version = getattr(settings, "VIRES_SERVICE_TERMS_VERSION", None)

    def _get_consented_version(user):
        try:
            profile = user.userprofile
        except ObjectDoesNotExist:
            return None
        return profile.consented_service_terms_version

    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if request.user.is_authenticated and required_version:
            if _get_consented_version(request.user) != required_version:
                response = redirect('update_user_consent')
                response["Location"] += "?next=%s" % (
                    quote(request.get_full_path())
                )
                return response
        return view_func(request, *args, **kwargs)

    return _wrapper_
