#-------------------------------------------------------------------------------
#
#  customized django-allauth AccountAdapter
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context
from allauth.core.internal.httpkit import get_frontend_url
from allauth.utils import build_absolute_uri


def get_url(request, name):
    url = get_frontend_url(request, name)
    if not url:
        url = build_absolute_uri(request, reverse(name))
    return url


class AccountAdapter(DefaultAccountAdapter):
    """ Customized account adapter. """

    def send_account_already_exists_mail(self, email):

        signup_url = get_url(context.request, "account_signup")
        password_reset_url = get_url(context.request, "account_reset_password")
        socialaccount_connections_url = get_url(context.request, "socialaccount_connections")

        ctx = {
            "request": context.request,
            "signup_url": signup_url,
            "password_reset_url": password_reset_url,
            "socialaccount_connections_url": socialaccount_connections_url
        }
        self.send_mail("account/email/account_already_exists", email, ctx)
