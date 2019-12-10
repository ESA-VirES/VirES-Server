#-------------------------------------------------------------------------------
#
# User management - deactivate one or more active users
#
# Project: VirES
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
# pylint: disable=missing-docstring, too-few-public-methods

from logging import getLogger
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ._common import ConsoleOutput


class Command(ConsoleOutput, BaseCommand):
    logger = getLogger(__name__)

    help = (
        "Deactivate active users. The users are selected either by the "
        "provided user names (no user name - no output) or by the '--all' "
        "option. "
    )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("username", nargs="*")
        parser.add_argument(
            "-a", "--all", dest="all_users", action="store_true", default=False,
            help="Select all users."
        )

    def handle(self, *args, **kwargs):
        usernames = kwargs['username']
        qset = User.objects
        if kwargs['all_users']:
            qset = qset.all()
        else:
            if not usernames:
                self.warning(
                    "No username has provided! Use '--help' to get more "
                    "information of the command usage."
                )
            qset = qset.filter(username__in=usernames)

        for user in qset:
            if user.is_active:
                user.is_active = False
                user.save()
                self.info(
                    "User %s has been deactivated.", user.username, log=True
                )
            else:
                self.info(
                    "User %s is already inactive. No change needed.",
                    user.username
                )
