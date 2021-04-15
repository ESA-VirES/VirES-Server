#-------------------------------------------------------------------------------
#
# VirES specific views
#
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

import json
from logging import getLogger
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.messages import INFO, ERROR, add_message
from django.views.decorators.http import require_GET
from ..utils import get_next_redirect_url
from ..decorators import (
    redirect_unauthenticated, oauth2_protected, log_exception,
)
from ..forms import UserProfileForm
from ..models import Permission

USER_PROFILE_TEMPLATE = 'vires_oauth/index.html'
USER_CONSENT_TEMPLATE = 'account/consent.html'


def test_view(request):
    response = "\n".join([
        "\n".join("%s: %s" % (key, value) for key, value in request.META.items()),
        "\n".join("%s: %s" % (key, value) for key, value in request.headers.items()),
    ])
    return HttpResponse(response, 'text/plain', 200)


@require_GET
@oauth2_protected("read_id")
@log_exception(getLogger(__name__))
def api_user_view(request, *args, **kwargs):
    scopes = request.access_token.scopes
    user = request.user
    data = {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
    getLogger(__name__).debug("%s", data)
    if "read_email" in scopes:
        data["email"] = user.email
    if "read_permissions" in scopes:
        data["permissions"] = list(Permission.get_user_permissions(user))
    return HttpResponse(json.dumps(data), content_type="application/json")


@redirect_unauthenticated
def update_user_profile_view(request):
    form = UserProfileForm(request.user, request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save_profile(request.user)
            add_message(request, INFO, "Profile updated.")
            return redirect('account_update_profile')
        add_message(request, ERROR, "Profile update failed.")
    return render(request, USER_PROFILE_TEMPLATE, {
        'permissions': list(request.user.oauth_user_permissions.items()),
        'form': form,
    })


@redirect_unauthenticated
def update_user_consent_view(request):
    redirect_field = 'next'
    redirect_url = get_next_redirect_url(request, redirect_field)
    service_terms_version = getattr(
        settings, "VIRES_SERVICE_TERMS_VERSION", None
    )
    user_profile = request.user.userprofile
    if request.method == "POST":
        user_profile.consented_service_terms_version = service_terms_version
        user_profile.save()
        add_message(request, INFO, "Consent received.")
        return redirect(redirect_url or 'account_update_profile')
    return render(request, USER_CONSENT_TEMPLATE, {
        'consent_required': (
            user_profile.consented_service_terms_version != service_terms_version
        ),
        'redirect_field_name': redirect_field,
        'redirect_field_value': redirect_url,
    })
