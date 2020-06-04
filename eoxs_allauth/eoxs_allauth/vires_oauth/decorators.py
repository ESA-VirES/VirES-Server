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

import re
from logging import getLogger
from functools import wraps
from requests import RequestException
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.contrib.auth.models import User
from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount
from .permissions import get_user_permissions, get_required_permission
from .messages import add_message_access_denied
from .views import ViresOAuth2Adapter
from .provider import ViresProvider


def oauth_token_authentication(view_func):
    """ Perform VirES OAuth access token authentication. """
    # NOTE: Make sure the HTTP server is configured so that the Authorization
    #       header is passed to the WSGI interface (WSGIPassAuthorization On).
    re_bearer = re.compile(r"^Bearer (?P<token>[a-zA-Z0-9_-]{30,30})$")
    logger = getLogger(__name__ + ".oauth_token_authentication")

    def _extract_token(request):
        match = re_bearer.match(request.META.get("HTTP_AUTHORIZATION", ""))
        return match.groupdict()['token'] if match else None

    def _read_profile(token):
        response = ViresOAuth2Adapter.read_profile(token)
        if response.status_code == 200:
            return response.json()
        if response.status_code not in (403, 401):
            response.raise_for_status()
        return None

    def _get_user(username):
        try:
            if username:
                return User.objects.get(username=username)
        except User.DoesNotExist:
            pass
        return None

    @transaction.atomic
    def _create_new_user(profile):
        user = User(**{
            key: val for key, val
            in ViresProvider.extract_common_fields(profile).items() if val
        })
        user.last_login = user.date_joined
        user.save()
        social_account = SocialAccount(
            user=user,
            provider=ViresProvider.id,
            uid=ViresProvider.extract_uid(profile),
            extra_data=profile,
        )
        social_account.date_joined = user.date_joined
        social_account.last_login = user.last_login
        social_account.save()
        return user

    @wraps(view_func)
    def _wrapper_(request, *args, **kwargs):
        if not request.user.is_authenticated:
            try:
                profile = _read_profile(_extract_token(request))
            except RequestException as error:
                getLogger(__name__).error("OAuth server profile request failed: %s", error)
                return HttpResponse("Bad gateway", content_type='text/plain', status=502)
            if profile:
                user = _get_user(profile.get('username'))
                if not user:
                    try:
                        user = _create_new_user(profile)
                    except Exception as exception:
                        logger.error(
                            "Failed to create user %s! %s",
                            profile.get('username'),
                            exception, exc_info=True
                        )
                    else:
                        user_signed_up.send(
                            sender=user.__class__, request=request, user=user,
                        )
                        logger.debug("user %s created", user.username)
                if user and user.is_active:
                    user.vires_permissions = set(profile.get('permissions') or [])
                    request.user = user
        return view_func(request, *args, **kwargs)
    return _wrapper_


def authorized_only(view_func):
    """ Allow only authorized users or return 403 response. """

    def _reject_unauthorized_view(*args, **kwargs):
        raise PermissionDenied

    return _check_vires_authorization(view_func, _reject_unauthorized_view)


def logout_unauthorized(view_func):
    """ Log out unauthorized users. """

    def _logout_unauthorized_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            add_message_access_denied(request)
        return view_func(request, *args, **kwargs)

    return _check_vires_authorization(view_func, _logout_unauthorized_view)


def redirect_unauthorized(redirect_url):
    """ Log out and redirect unauthorized users. """

    def _redirect_unauthorized(view_func):

        def _redirect_unauthorized_view(request, *args, **kwargs):
            if request.user.is_authenticated:
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
