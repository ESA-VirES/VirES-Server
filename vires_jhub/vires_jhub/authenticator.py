#-------------------------------------------------------------------------------
#
# VirES Jupyter Hub authenticator
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
# pylint: disable=missing-docstring, too-many-ancestors, abstract-method

import os
import json
import urllib
from tornado.auth import OAuth2Mixin
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError
from jupyterhub.auth import LocalAuthenticator
from oauthenticator.oauth2 import OAuthLoginHandler, OAuthenticator


SCOPE = ["read_id", "read_permissions"]
SERVICE_NAME = "VirES"
ADMIN_PERMISSION_ENV = "VIRES_ADMIN_PERMISSION"
USER_PERMISSION_ENV = "VIRES_USER_PERMISSION"
CLIENT_SECRET_ENV = "VIRES_CLIENT_SECRET"
CLIENT_ID_ENV = "VIRES_CLIENT_ID"
CLIENT_SECRET_ENV = "VIRES_CLIENT_SECRET"
SERVER_URL_ENV = "VIRES_OAUTH_SERVER_URL"
DIRECT_SERVER_URL_ENV = "VIRES_OAUTH_DIRECT_SERVER_URL"


USER_PERMISSION = os.environ.get(USER_PERMISSION_ENV, "user")
ADMIN_PERMISSION = os.environ.get(ADMIN_PERMISSION_ENV, "admin")

SERVER_URL = os.environ[SERVER_URL_ENV].rstrip("/")
DIRECT_SERVER_URL = os.environ.get(DIRECT_SERVER_URL_ENV, SERVER_URL).rstrip("/")

AUTHORIZE_URL = "{0}/authorize/".format(SERVER_URL)
ACCESS_TOKEN_URL = "{0}/token/".format(DIRECT_SERVER_URL)
USER_PROFILE_URL = "{0}/user/".format(DIRECT_SERVER_URL)


class ViresLoginHandler(OAuthLoginHandler, OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL = AUTHORIZE_URL
    _OAUTH_ACCESS_TOKEN_URL = ACCESS_TOKEN_URL


class ViresOAuthenticator(OAuthenticator):
    login_service = SERVICE_NAME
    scope = SCOPE
    client_id_env = CLIENT_ID_ENV
    client_secret_env = CLIENT_SECRET_ENV
    login_handler = ViresLoginHandler
    admin_permission = ADMIN_PERMISSION
    user_permission = USER_PERMISSION

    async def authenticate(self, handler, data=None):
        http_client = AsyncHTTPClient()
        auth_state = await self._retrieve_access_token(http_client, handler)
        user_profile = await self._retrieve_user_profile(
            http_client, auth_state['access_token']
        )
        username = user_profile['username']
        permissions = set(user_profile['permissions'])

        is_authorised = self.user_permission in permissions
        if not is_authorised:
            self.log.warning("%s is not authorised", username)
            return None

        is_admin = self.admin_permission in permissions
        self.log.info("%s is authorized as %s", username, (
            "an administrator" if is_admin else "an ordinary user"
        ))

        return {
            "name": username,
            "admin": is_admin,
            "auth_state": auth_state,
        }

    async def _retrieve_user_profile(self, http_client, access_token):
        request = HTTPRequest(
            USER_PROFILE_URL,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer {}".format(access_token),
            },
        )
        response = await http_client.fetch(request)
        return json.loads(response.body.decode("utf8", "replace"))

    async def _retrieve_access_token(self, http_client, handler):
        parameters = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": handler.get_argument("code"),
        }
        request = HTTPRequest(
            ACCESS_TOKEN_URL,
            method="POST",
            headers={"Accept": "application/json"},
            body=urllib.parse.urlencode(parameters),
        )
        response = await http_client.fetch(request)
        data = json.loads(response.body.decode("utf8", "replace"))

        if "access_token" not in data:
            raise HTTPError(
                500, "Failed to retrieve access token! {}".format(response)
            )

        return data


class LocalViresOAuthenticator(LocalAuthenticator, ViresOAuthenticator):
    """ Version of the authenticator working with local system users. """
