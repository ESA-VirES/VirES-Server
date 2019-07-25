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
from traitlets import Unicode
from tornado.auth import OAuth2Mixin
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError
from jupyterhub.auth import LocalAuthenticator
from oauthenticator.oauth2 import OAuthLoginHandler, OAuthenticator

AUTHORIZE_PATH = "/authorize/"
ACCESS_TOKEN_PATH = "/token/"
USER_PROFILE_PATH = "/user/"


def _join_url(base, path):
    return base.rstrip("/") + path


class ViresLoginHandler(OAuthLoginHandler, OAuth2Mixin):
    # The server URL is configurable via the ViresOAuthenticator class.

    @property
    def _OAUTH_AUTHORIZE_URL(self):
        return _join_url(self.authenticator.server_url, AUTHORIZE_PATH)


class ViresOAuthenticator(OAuthenticator):
    login_service = "VirES"
    scope = ["read_id", "read_permissions"]
    client_id_env = "VIRES_CLIENT_ID"
    client_secret_env = "VIRES_CLIENT_SECRET"
    login_handler = ViresLoginHandler

    server_url = Unicode(
        os.environ.get("VIRES_OAUTH_SERVER_URL", ""),
        config=True,
        help="VirES OAuth2 server URL. "
    )

    direct_server_url = Unicode(
        os.environ.get("VIRES_OAUTH_DIRECT_SERVER_URL", ""),
        config=True,
        help="Optional server-side direct VirES OAuth2 server URL."
    )

    user_permission = Unicode(
        os.environ.get("VIRES_USER_PERMISSION", "user"),
        config=True,
        help="User permission required to grant access to JupyterHub."
    )

    admin_permission = Unicode(
        os.environ.get("VIRES_ADMIN_PERMISSION", "admin"),
        config=True,
        help="User permission required to grant JupyterHub administration right."
    )

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
            _join_url(self.direct_server_url or self.server_url, USER_PROFILE_PATH),
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
            _join_url(self.direct_server_url or self.server_url, ACCESS_TOKEN_PATH),
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
