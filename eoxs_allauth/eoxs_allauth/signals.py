#-------------------------------------------------------------------------------
#
#  Signal handlers - primarily access logging.
#
# Project: EOxServer - django-allauth integration.
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=missing-docstring, unused-argument

from logging import getLogger
from django.dispatch import receiver
from allauth.account.signals import (
    user_logged_in, user_signed_up, password_set, password_changed,
    password_reset, email_confirmed, email_confirmation_sent, email_changed,
    email_added, email_removed,
)
from allauth.socialaccount.signals import (
    pre_social_login, social_account_added, social_account_removed,
)

LOGGER = getLogger("eoxs_allauth")


@receiver(user_logged_in)
def receive_user_logged_in(request, user, **kwargs):
    LOGGER.info("%s logged in", user)


@receiver(user_signed_up)
def receive_user_signed_up(request, user, **kwargs):
    LOGGER.info("%s signed up", user)


@receiver(password_set)
def receive_password_set(request, user, **kwargs):
    LOGGER.info("%s set password ", user)


@receiver(password_changed)
def receive_password_changed(request, user, **kwargs):
    LOGGER.info("%s changed password", user)


@receiver(password_reset)
def receive_password_reset(request, user, **kwargs):
    LOGGER.info("%s reset password", user)


@receiver(email_changed)
def receive_email_changed(request, user, from_email_address, to_email_address,
                          **kwargs):
    LOGGER.info(
        "%s changed primary e-mail address from %s to %s",
        user, from_email_address.email, to_email_address.email
    )


@receiver(email_added)
def receive_email_added(request, user, email_address, **kwargs):
    LOGGER.info("%s added e-mail address %s", user, email_address.email)


@receiver(email_removed)
def receive_email_removed(request, user, email_address, **kwargs):
    LOGGER.info("%s removed e-mail address %s", user, email_address.email)


@receiver(email_confirmed)
def receive_email_confirmed(email_address, **kwargs):
    LOGGER.info(
        "%s confirmed e-mail address %s",
        email_address.user, email_address.email
    )


@receiver(email_confirmation_sent)
def receive_email_confirmation_sent(confirmation, **kwargs):
    LOGGER.info(
        "%s was sent a request to confirm e-mail address %s",
        confirmation.email_address.user, confirmation.email_address.email
    )


@receiver(pre_social_login)
def receive_pre_social_login(request, sociallogin, **kwargs):
    # TODO: find a better way how to guess the user's identity
    user_id = str(sociallogin.user)
    emails = ", ".join(addr.email for addr in sociallogin.email_addresses)
    if user_id:
        if emails:
            user_id += ", %s" % emails
    else:
        if emails:
            user_id = emails
        else:
            user_id = '<unknown>'
    LOGGER.info(
        "successful %s authentication of %s",
        sociallogin.account.provider, user_id
    )


@receiver(social_account_added)
def receive_social_account_added(request, sociallogin, **kwargs):
    LOGGER.info(
        "%s added %s account", sociallogin.user, sociallogin.account.provider
    )


@receiver(social_account_removed)
def receive_social_account_removed(request, socialaccount, **kwargs):
    LOGGER.info(
        "%s removed %s account", socialaccount.user, socialaccount.provider
    )
