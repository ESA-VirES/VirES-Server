#-------------------------------------------------------------------------------
#
# E-mail management - send confirmation e-mail to selected address
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

from allauth.account.models import EmailAddress
from .common import EmailSelectionSubcommandProtected


class SendConfirmationEmailSubcommand(EmailSelectionSubcommandProtected):
    name = "send_confirmation"
    help = "Send confirmation e-mail to the selected address."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--allow-verified", dest="allow_verified", action="store_true",
            default=False, help=(
                "Enable sending of confirmation e-mails to already verified "
                "users. By default, the confirmation is sent to unverified "
                "users only."
            )
        )

    def handle(self, **kwargs):
        emails = self.select_emails(
            EmailAddress.objects.prefetch_related('user'), **kwargs
        )
        for email in emails:
            self.send_confirmation(email, kwargs["allow_verified"])

    def send_confirmation(self, email, allow_verified):
        if email.verified and not allow_verified:
            self.info(
                "email %s/%s already verified, no confirmation sent",
                email.user.username, email.email
            )
        else:
            try:
                email.send_confirmation()
            except Exception as error:
                self.error(
                    "Failed to send the confirmation email %s/%s! %s",
                    email.user.username, email.email, error
                )
            else:
                self.info(
                    "confirmation email sent to %s/%s",
                    email.user.username, email.email, log=True
                )
