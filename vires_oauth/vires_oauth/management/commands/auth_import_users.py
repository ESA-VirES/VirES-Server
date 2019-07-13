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
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils.dateparse import parse_datetime
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from ...models import UserProfile
from ._common import ConsoleOutput


class Command(ConsoleOutput, BaseCommand):
    help = "Import users from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input file-name. "
                "By default it is read from the standard input."
            )
        )

    def handle(self, filename, **kwargs):

        with sys.stdin.buffer if filename == "-" else open(filename, "rb") as file_:
            data = json.load(file_)

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
                self.info((
                    "Existing user %s updated." if is_updated else
                    "New user %s created."
                ), name)

        if created_count:
            self.info(
                "%d of %d user%s updated.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d user%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d user%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )

#-------------------------------------------------------------------------------

def _parse_datetime(value):
    return None if value is None else parse_datetime(value)

PARSERS = {
    "date_joined": _parse_datetime,
    "last_login": _parse_datetime,
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

    set_user_profile(user, data.get("user_profile"))
    set_email_addresses(user, data.get("email_addresses", []))
    set_social_accounts(user, data.get("social_accounts", []))

    # set optional user groups
    groups = data.get('groups')
    if groups is None:
        groups = []
        # set the default group for new
        default_group = getattr(settings, "VIRES_OAUTH_DEFAULT_GROUP", None)
        if not is_updated and default_group:
            groups.append(default_group)

    set_groups(user, groups)

    return is_updated


def get_user(username):
    try:
        return True, User.objects.get(username=username)
    except User.DoesNotExist:
        return False, User(username=username)


def set_groups(user, group_names):
    groups = get_groups()
    for group_name in group_names:
        try:
            user.groups.add(groups[group_name])
        except KeyError:
            ConsoleOutput.warning(
                "User %s cannot be assigned to a group %s. "
                "The group does not exist" % (user.username, group_name)
            )

def get_groups():
    """ Get a dictionary of the existing user groups. """
    return {group.name: group for group in Group.objects.all()}

#-------------------------------------------------------------------------------

USER_PROFILE_FIELDS = [
    "title", "institution", "country", "study_area", "executive_summary",
]


def set_user_profile(user, data):
    if data is None:
        return
    user_profile = get_user_profile(user)
    set_model(user_profile, USER_PROFILE_FIELDS, data)
    user_profile.save()


def get_user_profile(user):
    try:
        return user.userprofile
    except UserProfile.DoesNotExist:
        return UserProfile(user=user)

#-------------------------------------------------------------------------------

EMAIL_ADDRESS_FIELDS = ["verified", "primary"]


def set_email_addresses(user, data):
    for item in data:
        set_email_address(user, item)


def set_email_address(user, data):
    email_address = get_email_address(user, data['email'])
    set_model(email_address, EMAIL_ADDRESS_FIELDS, data)
    email_address.save()

    if email_address.primary:
        set_primary_email(user, email_address.email)


def set_primary_email(user, email):
    for item in user.emailaddress_set.all():
        if item.primary and item.email != email:
            item.primary = False
            item.save()
    user.email = email
    user.save()


def get_email_address(user, email):
    try:
        return user.emailaddress_set.get(email=email)
    except EmailAddress.DoesNotExist:
        return EmailAddress(user=user, email=email)

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
        return SocialAccount(provider=provider)

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
