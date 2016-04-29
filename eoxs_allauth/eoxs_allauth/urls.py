#-------------------------------------------------------------------------------
#
# Project: EOxServer - django-allauth integration.
# Authors: Daniel Santillan <daniel.santillan@eox.at>
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

from logging import INFO, WARNING
from django.conf.urls import url
from allauth.urls import urlpatterns as allauth_urlpatterns
from .views import ProfileUpdate
from .url_tools import decorate
from .decorators import log_access

# for the following URLs patterns a warning is logged in case
# on an unauthenticated access
WATCHED_URLS = [
    'account_logout',
    'account_change_password',
    'account_set_password',
    'account_inactive',
    'account_email',
    'socialaccount_connections',
]

# include AllAuth URL patters and wrap selected views
urlpatterns = decorate(
    allauth_urlpatterns, log_access(INFO, WARNING),
    lambda obj: obj.name in WATCHED_URLS
)

# additional patterns
urlpatterns += [
    url(r'^profile/$', ProfileUpdate.as_view(), name='account_change_profile'),
]
