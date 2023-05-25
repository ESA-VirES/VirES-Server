#-------------------------------------------------------------------------------
#
#  EOIAM provider - views - base classes
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021-2023 EOX IT Services GmbH
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

import requests
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter


class EoiamOAuth2AdapterBase(OAuth2Adapter):
    basic_auth = True # pass client credentials via the HTTP Basic authentication
    provider_id = None
    settings = None

    # URL used for browser-to-server connections
    server_url = None

    access_token_url = None
    authorize_url = None
    profile_url = None

    @classmethod
    def read_profile(cls, token):
        headers = {'Authorization': f'Bearer {token}'}
        return requests.get(cls.profile_url, headers=headers)

    def complete_login(self, request, app, token, response):
        extra_data = self.read_profile(token.token).json()
        return self.get_provider().sociallogin_from_response(request, extra_data)

    def get_email(self, token):
        raise NotImplementedError
