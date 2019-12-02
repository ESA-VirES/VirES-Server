#-------------------------------------------------------------------------------
#
# VirES OAuth2 server URLs
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring,invalid-name

from django.urls import path, include, re_path
from oauth2_provider.views import (
    AuthorizationView,
    TokenView,
    RevokeTokenView,
    IntrospectTokenView,
    #ApplicationList,
    #ApplicationRegistration,
    #ApplicationDetail,
    #ApplicationDelete,
    #ApplicationUpdate,
    #AuthorizedTokensListView,
    #AuthorizedTokenDeleteView,
)
from .views import (
    AdminApplicationList,
    AdminApplicationDetail,
    AdminApplicationDelete,
    AdminApplicationUpdate,
    AdminApplicationRegistration,
    FilteredAuthorizedTokensListView,
    FixedAuthorizedTokenDeleteView,
    update_user_profile_view,
    update_user_consent_view,
    api_user_view,
)
from .decorators import has_permission, request_consent


vires_admin_only = has_permission('admin')


oauth2_provider_urlpatterns = [

    # Base views
    path(
        "authorize/",
        request_consent(AuthorizationView.as_view()),
        name="authorize"
    ),
    path(
        "token/",
        TokenView.as_view(),
        name="token"
    ),
    path(
        "revoke_token/",
        RevokeTokenView.as_view(),
        name="revoke-token"
    ),
    path(
        "introspect/",
        IntrospectTokenView.as_view(),
        name="introspect"
    ),

    # Application management views
    path(
        "applications/",
        vires_admin_only(AdminApplicationList.as_view()),
        name="list"
    ),
    path(
        "applications/register/",
        vires_admin_only(AdminApplicationRegistration.as_view()),
        name="register"
    ),
    re_path(
        r"^applications/(?P<pk>[\w-]+)/$",
        vires_admin_only(AdminApplicationDetail.as_view()),
        name="detail"
    ),
    re_path(
        r"^applications/(?P<pk>[\w-]+)/delete/$",
        vires_admin_only(AdminApplicationDelete.as_view()),
        name="delete"
    ),
    re_path(
        r"^applications/(?P<pk>[\w-]+)/update/$",
        vires_admin_only(AdminApplicationUpdate.as_view()),
        name="update"
    ),

    # Token management views
    path(
        "authorized_tokens/",
        FilteredAuthorizedTokensListView.as_view(),
        name="authorized-token-list"
    ),
    re_path(
        r"^authorized_tokens/(?P<pk>[\w-]+)/delete/$",
        FixedAuthorizedTokenDeleteView.as_view(),
        name="authorized-token-delete"
    ),
]

urlpatterns = [
    path('', request_consent(update_user_profile_view), name='account_update_profile'),
    path('', include((oauth2_provider_urlpatterns, "oauth2_provider"))),
    path('consent/', update_user_consent_view, name="update_user_consent"),
    path('user/', api_user_view),
    path('accounts/', include('allauth.urls')),
]
