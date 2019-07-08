#-------------------------------------------------------------------------------
#
# custom OAuth2 provider views
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
# pylint: disable=missing-docstring,too-many-ancestors

from django.forms.models import modelform_factory
from django.utils import timezone
from oauth2_provider.models import get_application_model
from oauth2_provider.views import (
    ApplicationRegistration,
    ApplicationUpdate,
    AuthorizedTokensListView,
    AuthorizedTokenDeleteView,
)


APP_FIELDS = [
    "name",
    "client_id",
    "client_secret",
    "client_type",
    "authorization_grant_type",
    "skip_authorization",
    "redirect_uris"
]

APP_FIELD_LABELS = {
    "name": "Application Name",
    "client_id": "Client Id",
    "client_secret": "Client Secret",
    "client_type": "Client Type",
    "authorization_grant_type": "Authorization Grant Type",
    "skip_authorization": "Skip Authorization (Trusted App)",
    "redirect_uris": "Callback URIs",
}

class AdminApplicationRegistration(ApplicationRegistration):
    """ App registration form with extra fields. """
    def get_form_class(self):
        return modelform_factory(
            get_application_model(), fields=APP_FIELDS, labels=APP_FIELD_LABELS
        )

    def get_initial(self):
        model = get_application_model()
        initial_data = super().get_initial()
        initial_data.update({
            "client_type": model.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": model.GRANT_AUTHORIZATION_CODE,
        })
        return initial_data


class AdminApplicationUpdate(ApplicationUpdate):
    """ App update form with extra fields.  """
    def get_form_class(self):
        return modelform_factory(
            get_application_model(), fields=APP_FIELDS, labels=APP_FIELD_LABELS
        )


class FilteredAuthorizedTokensListView(AuthorizedTokensListView):
    """ Token list view. """
    def get_queryset(self):
        # remove expired tokens
        super().get_queryset().filter(
            user=self.request.user, expires__lte=timezone.now()
        ).delete()
        return super().get_queryset().select_related("application").filter(
            user=self.request.user, expires__gt=timezone.now()
        ).order_by("-created")


class FixedAuthorizedTokenDeleteView(AuthorizedTokenDeleteView):
    """ Token removal view. """
    context_object_name = "token"
