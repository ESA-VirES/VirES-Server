#-------------------------------------------------------------------------------
#
#  EOIAM provider - "social account" provider class - common base
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021-2025 EOX IT Services GmbH
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

from logging import getLogger
from allauth.account.models import EmailAddress
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from .utils import update_user_groups_from_permissions


class EoiamAccount(ProviderAccount):

    def to_str(self):
        dflt = super().to_str()
        return self.account.extra_data.get("sub", dflt)


class EoiamProviderBase(OAuth2Provider):
    id = None
    logger_name = None
    name = "EO Sign In"
    account_class = EoiamAccount
    oauth2_adapter_class = None

    settings = {}

    # A dictionary holding a list of alternative combinations EOIAM permissions
    # required to grant a group membership. If none of the listed combinations
    # is met the user cannot be a member of the given group.
    required_group_permissions = {
        group_name: list(map(frozenset, required_permissions))
        for group_name, required_permissions
        in settings.get("REQUIRED_GROUP_PERMISSIONS", {}).items()
    }

    @staticmethod
    def get_default_scope():
        return ["openid"] # "profile", "email"

    @staticmethod
    def extract_uid(data):
        return data["sub"]

    @staticmethod
    def extract_extra_data(data):

        if "Institution" in data:
            data["institution"] = data.pop("Institution")

        if "Oa-Signed-Tcs" in data:
            permissions = data.get("Oa-Signed-Tcs")
            if isinstance(permissions, str):
                permissions = permissions.split(",")
        else:
            permissions = []

        data["permissions"] = permissions

        return data

    @staticmethod
    def extract_common_fields(data):
        return {
            "username": data["sub"],
            "email": data["email"],
            "first_name": data.get("given_name"),
            "last_name": data.get("family_name"),
        }

    @classmethod
    def extract_email_addresses(cls, data):
        return [EmailAddress(
            email=data["email"],
            verified=bool(cls.settings.get("TRUST_EMAILS", False)),
            primary=True
        )]

    @classmethod
    def populate_user_from_extra_data(cls, user, extra_data):
        update_user_groups_from_permissions(
            user,
            set(extra_data["permissions"]),
            cls.required_group_permissions,
            logger=getLogger(cls.logger_name),
        )


def extract_eoiam(extra_data):
    """ Extract user info from an EO-IAM user profile. """
    data = {}
    data["email2"] = extra_data["email"]
    for key in ("country", "institution"):
        if key in extra_data:
            data[key] = extra_data[key]
    return data
