#-------------------------------------------------------------------------------
#
# User management - remove users from groups
#
# Authors: Martin Paces <martin.paces@eox.at>
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

from django.db import transaction
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from ...models import UserProfile
from ._common import CommandMixIn


class Command(CommandMixIn, BaseCommand):
    help = (
        "Remove selected users from a group. The users are selected either by the "
        "provided user names (no user name - no output) or by the '--all' "
        "option. "
    )

    def add_arguments(self, parser):
        parser.add_argument("users", nargs="*", help="Selected users.")
        parser.add_argument(
            "-g", "--group", dest="groups", required=True, nargs="+",
            help="Target group."
        )
        parser.add_argument(
            "-a", "--all", dest="all_users", action="store_true", default=False,
            help="Select all users."
        )

    def handle(self, groups, users, all_users, **kwargs):
        groups = list(Group.objects.filter(name__in=groups))

        if not groups:
            return

        group_string = "group%s %s" % (
            "s" if len(groups) > 1 else "",
            ", ".join(group.name for group in groups)
        )

        query = User.objects
        if all_users:
            query = query.all()
        else:
            if not users:
                self.warning(
                    "No user name has been provided! Use '--help' to get more "
                    "information of the command usage."
                )
            query = query.filter(username__in=users)

        for user in query:
            try:
                with transaction.atomic():
                    for group in groups:
                        user.groups.remove(group)
            except Exception as error:
                self.error(
                    "Failed to remove user %s from %s! %s", user.username,
                    group_string, error
                )
            else:
                self.info("user %s removed form %s", user.username, group_string)
