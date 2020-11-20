#-------------------------------------------------------------------------------
#
# Email management - list e-mails
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
from .common import EmailSelectionSubcommand


class ListEmailSubcommand(EmailSelectionSubcommand):
    name = "list"
    help = "List e-mails and their owners."

    def handle(self, **kwargs):
        emails = self.select_emails(
            EmailAddress.objects.prefetch_related('user'), **kwargs
        )

        for email in emails.all():
            print_email(email)


def print_email(email):
    labels = " ".join(
        " %s" % label for label in [
            "VERIFIED" if email.verified else "",
            "PRIMARY" if email.primary else "",
        ] if label
    )
    print("%s/%s%s" % (email.user.username, email.email, labels))
