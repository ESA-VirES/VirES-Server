#-------------------------------------------------------------------------------
#
# User record import
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

from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import User, Group
from django.utils.dateparse import parse_datetime
from django.contrib.auth.hashers import make_password
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from vires_oauth.models import UserProfile


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
def save_user(data, logger):
    if "password" not in data and "raw_password" in data:
        data["password"] = make_password(data.pop("raw_password") or None)

    is_updated, user = get_user(data["username"])
    set_model(user, USER_FIELDS, data, PARSERS)
    user.save()

    set_user_profile(user, data.get("user_profile", {}))
    set_email_addresses(user, data.get("email_addresses", []))
    set_social_accounts(user, data.get("social_accounts", []))

    # set optional user groups
    groups = data.get('groups')
    if groups is None:
        groups = []
        # set the default groups for a new user
        if not is_updated:
            groups.extend(getattr(settings, "VIRES_OAUTH_DEFAULT_GROUPS", []))

    set_groups(user, groups, logger)

    return is_updated


def get_user(username):
    try:
        return True, User.objects.get(username=username)
    except User.DoesNotExist:
        return False, User(username=username)


def set_groups(user, group_names, logger):
    all_groups = get_groups()

    for group in list(user.groups.exclude(name__in=group_names)):
        try:
            user.groups.remove(group)
        except KeyError:
            logger.warning(
                "Failed to remove user %s from the group %s!",
                user.username, group.name, log=True
            )

    for group_name in group_names:
        try:
            user.groups.add(all_groups[group_name])
        except KeyError:
            logger.warning(
                "User %s cannot be assigned to a group %s. "
                "The group does not exist", user.username, group_name, log=True
            )

def get_groups():
    """ Get a dictionary of the existing user groups. """
    return {group.name: group for group in Group.objects.all()}

#-------------------------------------------------------------------------------

USER_PROFILE_FIELDS = [
    "title", "institution", "country", "study_area", "executive_summary",
    "consented_service_terms_version",
]


def set_user_profile(user, data):
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

    remove_extra_email_addresses(user, data)

    for item in data:
        set_email_address(user, item)

    fix_primary_email(user)


def set_email_address(user, data):
    email_address = get_email_address(user, data['email'])
    set_model(email_address, EMAIL_ADDRESS_FIELDS, data)
    email_address.save()

    if email_address.primary:
        set_primary_email(user, email_address.email)


def set_primary_email(user, email):
    for item in user.emailaddress_set.exclude(email=email):
        item.primary = False
        item.save()
    user.email = email
    user.save()


def fix_primary_email(user):
    if not user.email:
        return

    for item in user.emailaddress_set.exclude(email=user.email):
        item.primary = False
        item.save()

    email = get_email_address(user, user.email)
    email.primary = True
    email.save()


def remove_extra_email_addresses(user, data):
    preserved_addresses = {item['email'] for item in data}
    if user.email:
        preserved_addresses.add(user.email)
    return user.emailaddress_set.exclude(email__in=preserved_addresses).delete()


def get_email_address(user, email):
    try:
        return user.emailaddress_set.get(email=email)
    except EmailAddress.DoesNotExist:
        return EmailAddress(user=user, email=email)

#-------------------------------------------------------------------------------

SOCIAL_ACCOUNT_FIELDS = ["uid", "date_joined", "last_login", "extra_data"]


def set_social_accounts(user, data):
    remove_extra_social_accounts(user, data)

    for item in data:
        set_social_account(user, item)


def set_social_account(user, data):
    social_account = get_social_account(user, data['provider'])
    set_model(social_account, SOCIAL_ACCOUNT_FIELDS, data, PARSERS)
    social_account.save()


def remove_extra_social_accounts(user, data):
    preserved_accounts = {item['provider'] for item in data}
    return user.socialaccount_set.exclude(provider__in=preserved_accounts).delete()


def get_social_account(user, provider):
    try:
        return user.socialaccount_set.get(provider=provider)
    except SocialAccount.DoesNotExist:
        return SocialAccount(user=user, provider=provider)

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
