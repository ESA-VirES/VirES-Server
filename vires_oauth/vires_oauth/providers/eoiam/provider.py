#-------------------------------------------------------------------------------
#
#  EOIAM provider - "social account" provider class
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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

from allauth.account.models import EmailAddress
from allauth.socialaccount import app_settings
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class EoiamAccount(ProviderAccount):

    def get_profile_url(self):
        return None
        #return self.account.extra_data.get( ... TBD ... )

    def get_avatar_url(self):
        return None
        #return self.account.extra_data.get( ... TBD ... )

    def to_str(self):
        dflt = super(EoiamAccount, self).to_str()
        return self.account.extra_data.get("sub", dflt)


class EoiamProvider(OAuth2Provider):
    id = 'eoiam'
    name = 'EO Sign In'
    account_class = EoiamAccount

    settings = app_settings.PROVIDERS.get(id, {})

    @staticmethod
    def get_default_scope():
        return ["openid"] # "profile", "email"

    @staticmethod
    def extract_uid(data):
        return data['sub']

    @staticmethod
    def extract_common_fields(data):
        return {
            'username': data['sub'],
            'email': data['sub'],
            'first_name': data.get('given_name'),
            'last_name': data.get('family_name'),
        }

    @classmethod
    def extract_email_addresses(cls, data):
        return [EmailAddress(
            email=data['sub'],
            verified=bool(cls.settings.get('TRUST_EMAILS', False)),
            primary=True
        )]

provider_classes = [EoiamProvider]
