#-------------------------------------------------------------------------------
#
# Connect existing users to the VirES OAuath server.
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
# pylint: disable=missing-docstring

from logging import getLogger
from django.db import transaction
from django.utils.timezone import now
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from ...models import UserProfile
from ._common import ConsoleOutput


class Command(ConsoleOutput, BaseCommand):
    logger = getLogger(__name__)

    help = (
        "Connect existing users to the OAuth server. "
        "By default all users are connected."
    )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("username", nargs="*")

    def handle(self, *args, **kwargs):
        usernames = kwargs["username"]
        query = User.objects
        if not usernames:
            query = query.all()
        else:
            query = query.filter(username__in=usernames)
        for user in query:
            self.connect_user(user)

    @transaction.atomic
    def connect_user(self, user):

        # wipe out e-mails
        user.emailaddress_set.all().delete()

        # wipe out profiles
        try:
            user.userprofile.delete()
        except UserProfile.DoesNotExist:
            pass

        # wipe out social accounts
        has_vires_connection = False
        for account in user.socialaccount_set.all():
            if account.provider == "vires" and account.uid == user.username:
                has_vires_connection = True
            else:
                account.delete()

        if has_vires_connection:
            self.info("User %s is already connected.", user.username)
            return

        try:
            account = SocialAccount.objects.get(
                uid=user.username, provider="vires"
            )
            account.user = user
            account.save()
        except SocialAccount.DoesNotExist:
            SocialAccount(
                provider="vires",
                user=user,
                uid=user.username,
                date_joined=now(),
                extra_data={}
            ).save()

        self.info("User %s connected.", user.username, log=True)
