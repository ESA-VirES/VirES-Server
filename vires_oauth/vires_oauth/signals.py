#-------------------------------------------------------------------------------
#
# VirES OAuth2  signal handlers
#
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=missing-docstring, invalid-name, unused-argument

from logging import getLogger
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from oauth2_provider.signals import app_authorized
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount import providers
from allauth.account.signals import (
    user_logged_in, user_signed_up, password_set, password_changed,
    password_reset, email_confirmed, email_confirmation_sent, email_changed,
    email_added, email_removed,
)
from allauth.socialaccount.signals import (
    social_account_added, social_account_removed,
)
from .utils import AccessLoggerAdapter, for_sender

ACCESS_LOGGER_NAME_ALLAUTH = "access.auth"
ACCESS_LOGGER_NAME_OAUTH2 = "access.oauth2_provider"


@receiver(post_save)
@for_sender(SocialAccount)
def receive_post_save(sender, instance, created, *args, **kwargs):
    provider = instance.get_provider()
    if hasattr(provider, "populate_user_from_extra_data"):
        provider.populate_user_from_extra_data(
            instance.user, instance.extra_data
        )


@receiver(user_signed_up)
def set_default_group(sender, request, user, **kwargs):
    """ Set default groups for newly signed-up users. """
    logger = getLogger(__name__)
    default_groups = getattr(settings, "VIRES_OAUTH_DEFAULT_GROUPS", [])
    if not default_groups:
        return
    groups = {
        group.name: group
        for group in Group.objects.filter(name__in=default_groups)
    }
    for group_name in default_groups:
        group = groups.get(group_name)
        if group:
            user.groups.add(group)
            logger.info("user %s added to %s", user.username, group.name)
        else:
            logger.warning("Default group %s does not exist!", group_name)


@receiver(app_authorized)
def receive_app_authorized(request, token, **kwargs):
    app_info = [("client_id", token.application.client_id)]
    if token.application.name:
        app_info.append(("name", token.application.name))
    _get_access_logger(request, token.user, ACCESS_LOGGER_NAME_ALLAUTH).info(
        "oauth application authorized (%s)" % _items2str(app_info)
    )


@receiver(user_logged_in)
def receive_user_logged_in(request, user, sociallogin=None, **kwargs):
    socialaccount = sociallogin.account if sociallogin else None
    _get_access_logger(request, user).info(
        "user logged in %s", _extract_login_info(socialaccount)
    )


@receiver(user_signed_up)
def receive_user_signed_up(request, user, sociallogin=None, **kwargs):
    socialaccount = sociallogin.account if sociallogin else None
    _get_access_logger(request, user).info(
        "user signed up %s", _extract_login_info(socialaccount)
    )


@receiver(password_set)
def receive_password_set(request, user, **kwargs):
    _get_access_logger(request, user).info("password set")


@receiver(password_changed)
def receive_password_changed(request, user, **kwargs):
    _get_access_logger(request, user).info("password changed")


@receiver(password_reset)
def receive_password_reset(request, user, **kwargs):
    _get_access_logger(request, user).info("password reset")


@receiver(email_changed)
def receive_email_changed(request, user, from_email_address, to_email_address,
                          **kwargs):
    _get_access_logger(request, user).info(
        "primary e-mail changed from %s to %s",
        from_email_address.email, to_email_address.email
    )


@receiver(email_added)
def receive_email_added(request, user, email_address, **kwargs):
    _get_access_logger(request, user).info(
        "new e-mail %s added", email_address.email
    )


@receiver(email_removed)
def receive_email_removed(request, user, email_address, **kwargs):
    _get_access_logger(request, user).info(
        "e-mail %s removed", email_address.email
    )


@receiver(email_confirmed)
def receive_email_confirmed(email_address, **kwargs):
    _get_access_logger(None, email_address.user).info(
        "e-mail %s confirmed", email_address.email
    )


@receiver(email_confirmation_sent)
def receive_email_confirmation_sent(confirmation, **kwargs):
    _get_access_logger(None, confirmation.email_address.user).info(
        "e-mail confirmation request sent to %s",
        confirmation.email_address.email
    )


@receiver(social_account_added)
def receive_social_account_added(request, sociallogin, **kwargs):
    _get_access_logger(request, sociallogin.user).info(
        "%s social account added %s", sociallogin.account.provider,
        _extract_user_info(sociallogin.account)
    )


@receiver(social_account_removed)
def receive_social_account_removed(request, socialaccount, **kwargs):
    _get_access_logger(request, socialaccount.user).info(
        "%s social account removed %s", socialaccount.provider,
        _extract_user_info(socialaccount)
    )


def _extract_login_info(social_account):
    if social_account:
        return "via %s social account %s" % (
            social_account.provider, _extract_user_info(social_account)
        )
    return "directly"


def _extract_user_info(social_account):
    social_provider = providers.registry.by_id(social_account.provider)
    data = social_provider.extract_common_fields(social_account.extra_data)

    first_name = data.pop('first_name', None)
    last_name = data.pop('last_name', None)
    if first_name and last_name:
        data['name'] = "%s %s" % (first_name, last_name)

    return "(%s)" % _items2str(
        (key, data.get(key)) for key in ['name', 'username', 'email']
    )


def _items2str(data):
    return ", ".join("%s: %s" % (key, value) for key, value in data if value)


def _get_access_logger(request, user, name=None):
    return AccessLoggerAdapter(
        getLogger(name or ACCESS_LOGGER_NAME_ALLAUTH),
        request, user=user
    )
