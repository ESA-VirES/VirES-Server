#-------------------------------------------------------------------------------
#
# E-mail management - verify e-mail address
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020 EOX IT Services GmbH
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

from logging import getLogger
from django.db import transaction
from allauth.account.models import EmailAddress
from ....utils import AccessLoggerAdapter
from ....signals import ACCESS_LOGGER_NAME_ALLAUTH
from .common import EmailSelectionSubcommandProtected


class VerifyEmailSubcommand(EmailSelectionSubcommandProtected):
    name = "verify"
    help = "Verify e-mail address"

    def get_access_logger(self, user):
        return AccessLoggerAdapter(
            getLogger(ACCESS_LOGGER_NAME_ALLAUTH), request=None, user=user,
        )

    def handle(self, **kwargs):
        emails = self.select_emails(
            EmailAddress.objects.prefetch_related('user'), **kwargs
        )
        for email in emails:
            self.verify_email(email)

    def verify_email(self, email):
        if email.verified:
            self.info(
                "email %s/%s already verified",
                email.user.username, email.email
            )
        else:
            try:
                verify_email(email)
            except Exception as error:
                self.error(
                    "Failed to update email %s/%s! %s",
                    email.user.username, email.email, error
                )
            else:
                self.get_access_logger(email.user).info(
                    "email %s confirmed manually by system administrator",
                    email.email
                )
                self.info(
                    "email %s/%s set as verified",
                    email.user.username, email.email, log=True
                )


@transaction.atomic
def verify_email(email):
    email.verified = True
    email.save()
