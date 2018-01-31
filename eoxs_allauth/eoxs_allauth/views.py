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

from logging import INFO, WARNING
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.forms.models import modelform_factory
from django_countries.widgets import CountrySelectWidget
from allauth.account.forms import LoginForm, SignupForm
from eoxserver.services.views import ows
from .models import UserProfile
from .decorators import log_access, authenticated_only


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


@require_GET
def workspace(request):
    """ EOxServer/allauth workspace.
    Note that the work space is used as the actual landing page.
    """
    # TODO: check if request.method is set to "POST"
    # if yes then login or signup user then do redirect or whatever
    login_form = LoginForm()
    del login_form.fields["login"].widget.attrs["autofocus"]
    return render(
        request, getattr(
            settings, 'WORKSPACE_TEMPLATE', "eoxs_allauth/workspace.html"
        ), {
            "login_form": login_form,
            "signup_form": SignupForm(),
        }
    )


class ProfileUpdate(SuccessMessageMixin, UpdateView):
    """ Custom profile update view. """
    model = UserProfile
    fields = [
        'title', 'institution', 'country', 'study_area', 'executive_summary',
    ]
    widgets = {
        'country': CountrySelectWidget(),
    }

    success_url = getattr(
        settings, 'PROFILE_UPDATE_SUCCESS_URL', '/accounts/profile/'
    )

    success_message = getattr(
        settings, 'PROFILE_UPDATE_SUCCESS_MESSAGE',
        'Profile was updated successfully.'
    )

    template_name = getattr(
        settings, 'PROFILE_UPDATE_TEMPLATE',
        'account/userprofile_update_form.html'
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
        return log_access(INFO, WARNING)(
            login_required(
                super(ProfileUpdate, cls).as_view(*args, **kwargs)
            )
        )
