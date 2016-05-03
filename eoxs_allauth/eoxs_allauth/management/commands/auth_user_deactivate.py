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

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, #nested_commit_on_success
)
from ...models import UserProfile


class Command(CommandOutputMixIn, BaseCommand):
    args = "<username> [<username> ...]"
    help = (
        "Deactivate active users. The users are selected either by the "
        "provided user names (no user name - no output) or by the '--all' "
        "option. "
    )
    option_list = BaseCommand.option_list + (
        make_option(
            "-a", "--all", dest="all_users", action="store_true", default=False,
            help="Select all users."
        ),
    )

    def handle(self, *args, **kwargs):
        # select user profile
        qset = UserProfile.objects.select_related('user')
        if kwargs["all_users"]:
            qset = qset.all()
        else:
            if not args:
                self.print_wrn(
                    "No user name has provided! Use '--help' to get more "
                    "information of the command usage."
                )
            qset = qset.filter(user__username__in=args)

        for profile in qset:
            if profile.user.is_active:
                profile.user.is_active = False
                profile.user.save()
                self.print_msg(
                    "User '%s' has been deactivated." % profile.user.username
                )
            else:
                self.print_msg(
                    "User '%s' is already inactive. No change needed." %
                    profile.user.username
                )
