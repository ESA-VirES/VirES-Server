#-------------------------------------------------------------------------------
#
# Import users from a JSON file.
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

import sys
import json
from traceback import print_exc
from django.db import transaction
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from allauth.socialaccount.models import SocialAccount
from eoxs_allauth.models import AuthenticationToken
from .._common import Subcommand


class ImportUserSubcommand(Subcommand):
    name = "import"
    help = "Import users from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input JSON file-name. "
                "By default, the users' definitions are read from standard "
                "input."
            )
        )

    def handle(self, **kwargs):
        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.save_users(json.load(file_), **kwargs)


    def save_users(self, data, **kwargs):
        failed_count = 0
        created_count = 0
        updated_count = 0
        for item in data:
            name = item.get("username")
            try:
                is_updated = save_user(item)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error("Failed to create or update user %s! %s", name, error)
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info(
                    "user %s updated" if is_updated else "user %s created",
                    name, log=True
                )

        if created_count:
            self.info(
                "%d of %d user%s created", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d user%s updated", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d user%s failed to be imported", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )
        sys.exit(failed_count)


def _parse_datetime(value):
    return None if value is None else parse_datetime(value)

PARSERS = {
    "date_joined": _parse_datetime,
    "last_login": _parse_datetime,
    "created": _parse_datetime,
    "expires": _parse_datetime,
}

USER_FIELDS = [
    "password", "is_active", "date_joined", "last_login",
    "first_name", "last_name", "email",
]


@transaction.atomic
def save_user(data):
    is_updated, user = get_user(data["username"])
    set_model(user, USER_FIELDS, data, PARSERS)
    user.save()

    set_social_accounts(user, data.get("social_accounts", []))
    set_access_tokens(user, data.get("access_tokens", []))

    return is_updated


def get_user(username):
    try:
        return True, User.objects.get(username=username)
    except User.DoesNotExist:
        return False, User(username=username)

#-------------------------------------------------------------------------------

SOCIAL_ACCOUNT_FIELDS = ["uid", "date_joined", "last_login", "extra_data"]


def set_social_accounts(user, data):
    for item in data:
        set_social_account(user, item)


def set_social_account(user, data):
    social_account = get_social_account(user, data['provider'])
    set_model(social_account, SOCIAL_ACCOUNT_FIELDS, data, PARSERS)
    social_account.save()


def get_social_account(user, provider):
    try:
        return user.socialaccount_set.get(provider=provider)
    except SocialAccount.DoesNotExist:
        return SocialAccount(user=user, provider=provider)

#-------------------------------------------------------------------------------

ACCESS_TOKEN_FIELDS = ["token", "purpose", "expires", "created"]

def set_access_tokens(user, data):
    for item in data:
        set_access_token(user, item)


def set_access_token(user, data):
    access_token = get_access_token(user, data['identifier'])
    set_model(access_token, ACCESS_TOKEN_FIELDS, data, PARSERS)
    access_token.save()


def get_access_token(user, identifier):
    try:
        return user.tokens.get(identifier=identifier)
    except AuthenticationToken.DoesNotExist:
        return AuthenticationToken(owner=user, identifier=identifier)

#-------------------------------------------------------------------------------

def set_model(object_, fields, data, parsers=None):
    parsers = parsers or {}
    for field in fields:
        value = data.get(field)
        parser = parsers.get(field)
        if parser is not None:
            value = parser(value)
        if value is not None:
            setattr(object_, field, value)
