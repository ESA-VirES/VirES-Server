#-------------------------------------------------------------------------------
#
#  VirES OAuth2 provider - "social account" provider views
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
# pylint: disable=missing-docstring

#
# Required settings:
#
# SOCIALACCOUNT_PROVIDERS = {
#     'vires': {
#         'SERVER_URL': <OAuth2 server URL>,
#     },
# }


import requests

from allauth.socialaccount import app_settings
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter, OAuth2CallbackView, OAuth2LoginView,
)
from allauth.socialaccount.providers.base.constants import AuthProcess
from .provider import ViresProvider


class ViresOAuth2Adapter(OAuth2Adapter):
    provider_id = ViresProvider.id
    settings = app_settings.PROVIDERS.get(provider_id, {})

    # URL used for browser-to-server connections
    public_server_url = settings['SERVER_URL'].rstrip('/')

    # URL used for server-to-server connection (must be absolute URI)
    direct_server_url = settings.get('DIRECT_SERVER_URL', public_server_url).rstrip('/')

    access_token_url = '{0}/token/'.format(direct_server_url)
    authorize_url = '{0}/authorize/'.format(public_server_url)
    profile_url = '{0}/user/'.format(direct_server_url)

    @classmethod
    def read_profile(cls, token):
        headers = {'Authorization': 'Bearer %s' % token}
        return requests.get(cls.profile_url, headers=headers)

    def complete_login(self, request, app, token, **kwargs):
        extra_data = self.read_profile(token.token).json()
        return self.get_provider().sociallogin_from_response(request, extra_data)

    def get_email(self, token):
        raise NotImplementedError


class ViresOAuth2LoginView(OAuth2LoginView):
    def login(self, request, *args, **kwargs):
        # prevent AuthProcess.REDIRECT and AuthProcess.CONNECT processes.
        process = request.GET.get("process")
        if process in (AuthProcess.REDIRECT, AuthProcess.CONNECT):
            request.GET = request.GET.copy()
            request.GET.pop("process")
        return super().login(request, *args, **kwargs)


oauth2_login = ViresOAuth2LoginView.adapter_view(ViresOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(ViresOAuth2Adapter)
