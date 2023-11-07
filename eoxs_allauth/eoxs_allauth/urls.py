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
# pylint: disable=missing-docstring, invalid-name

#from logging import INFO, WARNING
from django.conf.urls import include
from django.urls import re_path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.templatetags.static import static
from allauth.account.views import logout as account_logout, account_inactive
from allauth.socialaccount.views import (
    login_cancelled as socialaccount_login_cancelled,
    login_error as socialaccount_login_error,
)
from .views import (
    AccessTokenManagerView,
    AccessTokenCollectionAPIView,
    AccessTokenObjectAPIView,
)


urlpatterns = [
    re_path(
        r'^login/cancelled/$',
        socialaccount_login_cancelled,
        name='socialaccount_login_cancelled'
    ),
    re_path(
        r'^login/error/$',
        socialaccount_login_error,
        name='socialaccount_login_error'
    ),
    re_path(r'^', include('eoxs_allauth.vires_oauth.urls')),
    re_path(r"^logout/$", account_logout, name="account_logout"),
    re_path(r"^inactive/$", account_inactive, name="account_inactive"),
    re_path(r'^tokens/$', AccessTokenManagerView.as_view(), name='account_manage_access_tokens'),
    re_path(r'^api/tokens/?$', AccessTokenCollectionAPIView.as_view(), name='account_tokens_api'),
    re_path(r'^api/tokens/(?P<identifier>[A-Za-z0-9_-]{16,16})/?$', AccessTokenObjectAPIView.as_view()),
]

document_urlpatterns = [
    re_path(r'^%s$' % name, TemplateView.as_view(template_name=("documents/%s.html" % name)), name=name)
    for name in [
        'changelog',
        'custom_data_format_description',
        'faq',
        'service_terms',
        'privacy_notice',
    ]
] + [
    re_path(
        r'^data_terms$',
        RedirectView.as_view(url=static('other/T&C_for_ESA_Dataset-v1.pdf').replace("%", "%%")),
        name="data_terms"
    ),
]
