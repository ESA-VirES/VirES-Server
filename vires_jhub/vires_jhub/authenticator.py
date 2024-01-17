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
# pylint: disable=missing-docstring, too-few-public-methods

import os
import re
import ast
import json
from traitlets import Unicode, Dict
from tornado.auth import OAuth2Mixin
from jupyterhub.auth import LocalAuthenticator
from oauthenticator.oauth2 import OAuthLoginHandler, OAuthenticator

AUTHORIZE_PATH = "/authorize/"
ACCESS_TOKEN_PATH = "/token/"
USER_PROFILE_PATH = "/user/"
VIRES_TOKEN_API_PATH = "/accounts/api/tokens/"
VIRES_TOKEN_LIFESPAN = "PT15M"
RE_VIRES_URL = re.compile("(/(ows)?)?$")


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

    #def normalize_username(self, username):
    #    """ Override normalize_username to prevent username conversion
    #    to low-case and username mapping.
    #    """
    #    return username

    @property
    def token_url(self):
        """ See OAuthenticator.token_url for more details. """
        return _join_url(
            self.direct_server_url or self.server_url, ACCESS_TOKEN_PATH
        )

    @property
    def userdata_url(self):
        """ See OAuthenticator.userdata_url for more details. """
        return _join_url(
            self.direct_server_url or self.server_url, USER_PROFILE_PATH
        )

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

    instance_name = Unicode(
        os.environ.get("VIRES_INSTANCE_NAME", "VirES JupyterHub"),
        config=True,
        help="Name of the current VirES JupyterHub instance."
    )

    data_servers = Dict(
        ast.literal_eval(os.environ.get("VIRES_DATA_SERVERS", "{}")),
        config=True,
        help="A dictionary mapping VirES permissions to specific data servers."
    )

    default_data_server = Unicode(
        os.environ.get("VIRES_DEFAULT_DATA_SERVER", ""),
        config=True,
        help="Url of the default  VirES data server."
    )
    async def update_auth_model(self, auth_model):
        """ See OAuthenticator.update_auth_model(). """
        auth_state = auth_model.get("auth_state") or {}
        permissions = self._extract_permissions_from_auth_state(auth_state)
        # overwinding the default admin flag
        auth_model["admin"] = self.admin_permission in permissions
        # log the user information
        auth_state = auth_model.get("auth_state") or {}
        user_info = auth_state.get(self.user_auth_state_key) or {}
        self.log.info("user_info = %s", user_info)
        return auth_model

    async def check_allowed(self, username, auth_model):
        """ See OAuthenticator.check_allowed() """
        # A workaround for JupyterHub < 5.0 described in
        # https://github.com/jupyterhub/oauthenticator/issues/621
        if auth_model is None:
            return True

        auth_state = auth_model.get("auth_state") or {}
        permissions = self._extract_permissions_from_auth_state(auth_state)
        is_authorized = self.user_permission in permissions

        if not is_authorized:
            self.log.warning("%s is not authorised", username)
            return False

        is_admin = self.admin_permission in permissions
        self.log.info("%s is authorized as %s", username, (
            "an administrator" if is_admin else "an ordinary user"
        ))

        return True

    async def pre_spawn_start(self, user, spawner):
        """ Pass authentication details to spawner as environment variable. """
        auth_state = await user.get_auth_state()
        if not auth_state:
            self.log.warning(
                "User state is not available. "
                "VIRES_ACCESS_CONFIG will not be initialized."
            )
            return

        vires_access_config = json.dumps(
            await self._retrieve_vires_access_config(auth_state)
        )

        # KubeSpawner, unlike other spawners, uses Python string.format()
        # to expand environmental variables. This expansion breaks with JSON
        # data passed in an environment variable and the curly brackets
        # need to be escaped.
        if type(spawner).__name__ == "KubeSpawner":
            vires_access_config = (
                vires_access_config.replace("{", "{{").replace("}", "}}")
            )

        spawner.environment["VIRES_ACCESS_CONFIG"] = vires_access_config

    async def _retrieve_vires_access_config(self, auth_state):
        """ Retrieve access tokens for the configured VirES data servers. """
        access_token = self._extract_access_token_from_auth_state(auth_state)
        permissions = self._extract_permissions_from_auth_state(auth_state)

        return {
            "instance_name": self.instance_name,
            "default_server": self.default_data_server,
            "servers": await self._retrieve_vires_tokens(
                urls=[
                    url for permission, url in self.data_servers.items()
                    if permission in permissions
                ],
                oauth_token=access_token,
            ),
        }

    async def _retrieve_vires_tokens(self, urls, oauth_token):
        coroutines = [
            self._retrieve_vires_token(url, oauth_token) for url in urls
        ]
        tokens = {}
        for url, coroutine in zip(urls, coroutines):
            token = await coroutine
            if token:
                tokens[url] = token
        return tokens

    async def _retrieve_vires_token(self, server_url, oauth_token):
        """ Retrieve access token from the VirES API. """

        url = RE_VIRES_URL.sub(VIRES_TOKEN_API_PATH, server_url, count=1)

        headers = {
            "Authorization": f"Bearer {oauth_token}",
        }

        body = json.dumps({
            "expires": VIRES_TOKEN_LIFESPAN,
            "purpose": "VRE JupyterHub temporary token",
            "scopes": ["TokenMng"],
        })

        data = await self.httpfetch(
            url,
            method="POST",
            headers=headers,
            body=body.encode("utf-8"),
            validate_cert=self.validate_server_cert,
        )

        if not isinstance(data, dict):
            raise TypeError("Not a dictionary!")

        return {
            "token": data.get("token"),
            "expires": data.get("expires"),
        }

    def _extract_permissions_from_auth_state(self, auth_state):
        """ Extract permissions from the auth_state dictionary. """
        user_info = auth_state.get(self.user_auth_state_key) or {}
        permissions = set(user_info.get("permissions") or ())
        return permissions

    def _extract_access_token_from_auth_state(self, auth_state):
        """ Extract permissions from the auth_state dictionary. """
        return auth_state["access_token"]


class LocalViresOAuthenticator(LocalAuthenticator, ViresOAuthenticator):
    """ Version of the authenticator working with local system users. """
