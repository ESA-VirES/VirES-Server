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
from django.contrib.auth.models import Group
from allauth.account.signals import (
    user_logged_in, user_signed_up, password_set, password_changed,
    password_reset, email_confirmed, email_confirmation_sent, email_changed,
    email_added, email_removed,
)
from allauth.socialaccount.signals import (
    pre_social_login, social_account_added, social_account_removed,
)
from .utils import AccessLoggerAdapter


@receiver(user_signed_up)
def set_default_group(sender, request, user, **kwargs):
    """ Set default groups for newly signed-up users. """
    logger = getLogger(__name__)
    default_group = getattr(settings, "VIRES_OAUTH_DEFAULT_GROUP", None)
    if not default_group:
        return
    try:
        group = Group.objects.get(name=default_group)
    except Group.DoesNotExist:
        logger.warning("Default group %s does not exist!", default_group)
        return
    user.groups.add(group)
    logger.debug("User %s added to group %s.", user.username, group.name)



@receiver(user_logged_in)
def receive_user_logged_in(request, user, **kwargs):
    getLogger(__name__).info("%s: %s", request, user)
    _get_access_logger(request, user).info("user logged in")


@receiver(user_signed_up)
def receive_user_signed_up(request, user, **kwargs):
    _get_access_logger(request, user).info("new user signed up")


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


@receiver(pre_social_login)
def receive_pre_social_login(request, social_account, **kwargs):
    getLogger(__name__).debug(
        "%s: %s, %s", social_account, social_account.user, social_account.email_addresses
    )
    user = social_account.user

    #username = social_account.user.username
    #emails = ", ".join(addr.email for addr in social_account.email_addresses)
    #if user_id:
    #    if emails:
    #        user_id += ", %s" % emails
    #else:
    #    if emails:
    #        user_id = emails
    #    else:
    #        user_id = '<unknown>'
    _get_access_logger(request, user).info(
        "%s social account authentication", social_account.account.provider
    )


@receiver(social_account_added)
def receive_social_account_added(request, social_account, **kwargs):
    _get_access_logger(request, social_account.user).info(
        "%s social account added", social_account.account.provider
    )


@receiver(social_account_removed)
def receive_social_account_removed(request, social_account, **kwargs):
    _get_access_logger(request, social_account.user).info(
        "%s social account removed", social_account.account.provider
    )


def _get_access_logger(request, user):
    return AccessLoggerAdapter(
        getLogger("vires_oauth.allauth"), request, user=user
    )
