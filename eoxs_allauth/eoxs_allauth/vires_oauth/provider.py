#-------------------------------------------------------------------------------
#
#  VirES OAuth2 provider - "social account" provider class
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

from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from .settings import PROVIDER_ID, PROVIDER_NAME
from .views import ViresOAuth2Adapter


class ViresAccount(ProviderAccount):

    def get_profile_url(self):
        return self.account.extra_data.get("html_url")

    def get_avatar_url(self):
        return self.account.extra_data.get("avatar_url")

    def to_str(self):
        for key in ["name", "login"]:
            value = self.account.extra_data.get(key) or None
            if value:
                return value
        return super().to_str()


class ViresProvider(OAuth2Provider):
    id = PROVIDER_ID
    name = PROVIDER_NAME
    account_class = ViresAccount
    oauth2_adapter_class = ViresOAuth2Adapter

    @staticmethod
    def get_default_scope():
        return ["read_id"]

    @staticmethod
    def extract_uid(data):
        return data["username"]

    @staticmethod
    def extract_common_fields(data):
        return {
            "username": data["username"],
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email"),
        }


provider_classes = [ViresProvider]
