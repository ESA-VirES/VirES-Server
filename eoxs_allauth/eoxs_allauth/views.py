#-------------------------------------------------------------------------------
#
# Project: EOxServer - django-allauth integration.
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring, too-few-public-methods, too-many-ancestors

import json
from logging import INFO, WARNING
from django.conf import settings
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.forms.models import modelform_factory
from django.utils.timezone import now
from django_countries.widgets import CountrySelectWidget
from .models import UserProfile, AuthenticationToken
from .utils import datetime_to_string, parse_datetime_or_duration
from .decorators import (
    log_access, authenticated_only, token_authentication,
    csrf_protect_if_authenticated,
)
from .vires_oauth.decorators import (
    authorized_only, logout_unauthorized, redirect_unauthorized,
    oauth_token_authentication,
)


class JsonResponse(HttpResponse):
    """ JSON HTTP response. """
    def __init__(self, content, **kwargs):
        super().__init__(
            json.dumps(content), content_type="application/json", **kwargs
        )


def wrap_csrf_protected_api(view):
    """ Decorate protected API view.
    Requires CSRF token for the session-cookie (browser) authentication is used.
    """
    return _decorate(
        view,
        csrf_protect_if_authenticated,
        token_authentication,
        log_access(INFO, WARNING),
        authenticated_only,
        authorized_only,
        csrf_exempt,
    )


def wrap_protected_api(view):
    """ Decorate protected API view. """
    return _decorate(
        view,
        token_authentication,
        log_access(INFO, WARNING),
        authenticated_only,
        authorized_only,
        csrf_exempt,
    )


def wrap_open_api(view):
    """ Decorate protected API view. """
    return _decorate(
        view,
        log_access(INFO, WARNING),
        csrf_exempt,
    )


def _decorate(view, *decorators):
    for decorator in reversed(decorators):
        view = decorator(view)
    return view


def workspace(parse_client_state=None):
    """ EOxServer/allauth workspace.
    Note that the work space is used as the actual landing page.
    """
    allowed_methods = ["GET", "POST"] if parse_client_state else ["GET"]

    @log_access(INFO, INFO)
    @require_http_methods(allowed_methods)
    @logout_unauthorized
    @csrf_exempt
    def _workspace_view(request):
        if request.method == "POST" and parse_client_state:
            try:
                client_state = parse_client_state(
                    request.POST.get("client_state", "")
                )
            except ValueError:
                # TODO: implement a nicer error response
                return HttpResponse("Bad Request", "text/plain", 400)
        else:
            client_state = None

        return render(
            request, getattr(
                settings, "WORKSPACE_TEMPLATE", "eoxs_allauth/workspace.html"
            ), {
                "client_state": (
                    None if client_state is None else json.dumps(client_state)
                ),
            }
        )

    return _workspace_view


class ProfileUpdate(SuccessMessageMixin, UpdateView):
    """ Custom profile update view. """
    model = UserProfile
    fields = [
        "title", "institution", "country", "study_area", "executive_summary",
    ]
    widgets = {
        "country": CountrySelectWidget(),
    }

    success_url = getattr(
        settings, "PROFILE_UPDATE_SUCCESS_URL", "/accounts/profile/"
    )

    success_message = getattr(
        settings, "PROFILE_UPDATE_SUCCESS_MESSAGE",
        "Profile was updated successfully."
    )

    template_name = getattr(
        settings, "PROFILE_UPDATE_TEMPLATE",
        "account/userprofile_update_form.html"
    )

    def get_form_class(self):
        """ Get form class to be used by this view. """
        return modelform_factory(
            self.model, fields=self.fields, widgets=self.widgets
        )

    def get_object(self, queryset=None):
        """ Get the object displayed/ by the view. """
        return UserProfile.objects.get(user=self.request.user)

    @classmethod
    def as_view(cls, **kwargs):
        """ Return the actual Django view. """
        return _decorate(
            super(ProfileUpdate, cls).as_view(**kwargs),
            log_access(INFO, WARNING),
            login_required,
            redirect_unauthorized(reverse_lazy('workspace')),
        )


class AccessTokenManagerView(View):
    """ Access token manager view. """

    template_name = getattr(
        settings, "TEMPLATE_MANAGER",
        "account/access_token_manager.html"
    )

    @classmethod
    def as_view(cls, **kwargs):
        """ Return the actual Django view. """
        return _decorate(
            super(AccessTokenManagerView, cls).as_view(**kwargs),
            log_access(INFO, WARNING),
            login_required,
            redirect_unauthorized(reverse_lazy('workspace')),
        )

    def get(self, request):
        return render(request, self.template_name, {})


class APIView(View):

    @classmethod
    def as_view(cls, **kwargs):
        """ Return the actual Django view. """
        return _decorate(
            super().as_view(**kwargs),
            csrf_protect_if_authenticated,
            token_authentication,
            oauth_token_authentication,
            log_access(INFO, WARNING),
            authenticated_only,
            authorized_only,
            csrf_exempt,
        )

    @classmethod
    def error(cls, status, message):
        """ Error response"""
        return HttpResponse(
            "%s\n" % message, content_type="text/plain", status=status
        )

    @classmethod
    def not_found(cls):
        """ Not found response. """
        return cls.error(404, "Not found.")

    @classmethod
    def bad_request(cls):
        """ Bad request response """
        return cls.error(400, "Bad request.")

    @classmethod
    def no_response(cls):
        """ No response response. """
        return HttpResponse(status=204)


class AccessTokenCollectionAPIView(APIView):

    def get(self, request):
        """ List tokens. """
        return JsonResponse([
            AccessTokenAPI.serialize_token(token)
            for token in AccessTokenAPI.get_all_valid(request.user)
        ])

    def delete(self, request):
        """ Delete all tokens. """
        AccessTokenAPI.get_all(request.user).delete()
        return self.no_response()

    def post(self, request):
        """ Create new token. """
        try:
            token_request = AccessTokenAPI.parse_token_request(
                json.loads(request.body)
            )
        except (ValueError, TypeError):
            return self.bad_request()

        token_obj, token_str = AccessTokenAPI.create(
            request.user, **token_request
        )

        return JsonResponse({
            "token": token_str,
            **AccessTokenAPI.serialize_token(token_obj)
        })


class AccessTokenObjectAPIView(APIView):

    def get(self, request, identifier):
        """ Get valid token info for the given identifier. """
        try:
            return JsonResponse(
                AccessTokenAPI.serialize_token(
                    AccessTokenAPI.get_valid(request.user, identifier)
                )
            )
        except AuthenticationToken.DoesNotExist:
            return self.not_found()

    def delete(self, request, identifier):
        """ Delete valid token with the given identifier. """
        try:
            AccessTokenAPI.get_valid(request.user, identifier).delete()
        except AuthenticationToken.DoesNotExist:
            return self.not_found()
        return self.no_response()


class AccessTokenAPI:
    """ Access token management API. """

    @staticmethod
    def serialize_token(token):
        return {
            "identifier": token.identifier,
            "created": datetime_to_string(token.created),
            "expires": datetime_to_string(token.expires),
            "purpose": token.purpose,
        }

    @staticmethod
    def parse_token_request(data):
        if not isinstance(data, dict):
            raise TypeError("Not a valid token request!")
        token_request = {
            'expires': parse_datetime_or_duration(data.pop('expires', None)),
            'purpose': str(data.pop('purpose', '')),
        }
        if data:
            raise ValueError("Unexpected request fields!")
        return token_request

    @classmethod
    def create(cls, user, purpose=None, expires=None):
        token_obj = AuthenticationToken(
            owner=user,
            expires=(expires or None),
            purpose=(purpose or None),
        )
        token = token_obj.set_new_token()
        token_obj.save()
        return token_obj, token

    @classmethod
    def get_all(cls, user):
        """ Get all tokens. """
        return user.tokens.all().order_by("-created")

    @staticmethod
    def get_expired(user):
        return user.tokens.filter(expires__lte=now())

    @classmethod
    def get_all_valid(cls, user):
        """ Get all valid tokens. """
        cls.get_expired(user).delete()
        return cls.get_all(user)

    @classmethod
    def get_valid(cls, user, identifier):
        """ Get valid token for the given identifier """
        cls.get_expired(user).delete()
        return user.tokens.get(identifier=identifier)
