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
from time import sleep
from logging import INFO, WARNING
from datetime import datetime
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.forms.models import modelform_factory
from django.utils.timezone import now, is_aware, utc
from django.utils.dateparse import parse_datetime
from django_countries.widgets import CountrySelectWidget
from allauth.account.forms import LoginForm, SignupForm
from eoxserver.services.views import ows
from .models import UserProfile, AuthenticationToken
from .decorators import log_access, authenticated_only, token_authentication

@token_authentication
@log_access(INFO, WARNING)
@authenticated_only
@csrf_exempt
def wrapped_ows(request):
    """The EOxServer's OWS end-point view wrapped with the necessary decorators.
    """
    return ows(request)


@log_access(INFO, WARNING)
@csrf_exempt
def open_ows(request):
    """The EOxServer's OWS end-point view as non auth wrapped version
    with the necessary decorators.
    """
    return ows(request)


def parse_client_state(data):
    allowed_keys = [
        "serviceVersion",
        "timeSelection", "timeDomain", "areaSelection", "viewSelection",
        "productsConfiguration", "activeOverlays", "activeBaselayer",
        "cameraPosition", "xAxisSelection", "plotConfiguration",
        "parameterConfiguration", "filterSelection", "filtersMinimized",
    ]

    data = json.loads(data)

    if not isinstance(data, dict):
        raise ValueError

    return {
        key0: value for key0, value in (
            (key1, data.get(key1)) for key1 in allowed_keys
        ) if value is not None
    }


def workspace(parse_client_state=None):
    """ EOxServer/allauth workspace.
    Note that the work space is used as the actual landing page.
    """

    allowed_methods = ["GET", "POST"] if parse_client_state else ["GET"]

    @log_access(INFO, INFO)
    @require_http_methods(allowed_methods)
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

        login_form = LoginForm()
        del login_form.fields["login"].widget.attrs["autofocus"]
        return render(
            request, getattr(
                settings, "WORKSPACE_TEMPLATE", "eoxs_allauth/workspace.html"
            ), {
                "client_state": (
                    json.dumps(client_state) if client_state else None
                ),
                "login_form": login_form,
                "signup_form": SignupForm(),
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
    def as_view(cls, *args, **kwargs):
        """ Return the actual Djnago view. """
        view = super(ProfileUpdate, cls).as_view(*args, **kwargs)
        view = login_required(view)
        view = log_access(INFO, WARNING)(view)
        return view


class AccessTokenManagerView(View):
    """ Access token manager view. """

    template_name = getattr(
        settings, "TEMPLATE_MANAGER",
        "account/access_token_manager.html"
    )

    @classmethod
    def as_view(cls, *args, **kwargs):
        """ Return the actual Djnago view. """
        view = super(AccessTokenManagerView, cls).as_view(*args, **kwargs)
        view = login_required(view)
        view = log_access(INFO, WARNING)(view)
        return view

    def get(self, request):
        tokens = self._get_all_valid(request.user)

        # only a new not yet shown token can be displayed
        identifier = request.GET.get('show') or None
        new_token = self._get_new(request.user, identifier)
        if identifier and not new_token:
            # attempt to display already shown token
            return HttpResponseRedirect(request.path)

        return render(request, self.template_name, {
            "tokens": tokens,
            "new_token": new_token,
            "user": request.user,
            "isoformat": self._isoformat,
        })

    def post(self, request):
        new_token = None
        action = request.POST.get("action", "").lower()
        next_url = request.path

        if action == "create":
            try:
                new_token = self._create_new(
                    request.user, purpose=request.POST.get("purpose"),
                    expires=self._parse_datetime(request.POST.get("expires")),
                )
            except ValueError:
                pass # no change in case of an error
            else:
                # GET request that will display the token
                next_url = "%s?show=%s" % (next_url, new_token.identifier)

        elif action == "remove":
            self._delete(request.user, request.POST.get("identifier"))

        elif action == "remove-all":
            self._delete_all(request.user)

        return HttpResponseRedirect(next_url)

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        if not isinstance(value, datetime):
            try:
                parse_datetime(value)
            except (ValueError, KeyError, TypeError):
                raise ValueError
        if not is_aware(value):
            value = value.astimezone(utc)
        return value

    @staticmethod
    def _create_new(user, purpose=None, expires=None):
        token = AuthenticationToken()
        token.owner = user
        token.expires = expires or None
        token.purpose = purpose or None
        token.is_new = True  # token has not been displayed yet
        token.save()
        return token

    @staticmethod
    def _get_new(user, identifier):
        try:
            token = user.tokens.get(identifier=identifier)
        except AuthenticationToken.DoesNotExist:
            sleep(2)
            return None
        if token.is_new:
            token.is_new = False  # token will not be displayed again
            token.save()
            return token
        return None

    @classmethod
    def _get_all_valid(cls, user):
        cls._delete_expired(user)
        return user.tokens.all().order_by("-created")

    @staticmethod
    def _delete_expired(user):
        return user.tokens.filter(expires__lte=now()).delete()

    @staticmethod
    def _delete_all(user):
        return user.tokens.all().delete()

    @classmethod
    def _delete(cls, user, identifier):
        user.tokens.filter(identifier=identifier).delete()

    @staticmethod
    def _isoformat(value):
        return value.isoformat("T")
