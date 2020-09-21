#-------------------------------------------------------------------------------
#
# User management - insert users to one or more user groups
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
from django.contrib.auth.models import User, Group
from .common import UserSelectionSubcommandProtected


class SelectGroupMixIn():

    def select_groups(self, query, **kwargs):
        groups_requested = set(kwargs['groups'])
        groups = list(query.filter(name__in=groups_requested))
        groups_missing = groups_requested - {group.name for group in groups}
        for group_name in groups_missing:
            self.warning("User group %s does not exist!", group_name)
        return groups

    def get_groups_string(self, groups):
        return "group%s %s" % (
            "s" if len(groups) > 1 else "",
            ", ".join(group.name for group in groups)
        )


class SetUserGroupSubcommand(UserSelectionSubcommandProtected, SelectGroupMixIn):
    name = "set_group"
    help = "Insert users to one or more groups."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-g", "--group", dest="groups", action='append',
            required=True, help="Target user group."
        )

    def handle(self, **kwargs):
        users = self.select_users(User.objects.all(), **kwargs)
        groups = self.select_groups(Group.objects.all(), **kwargs)

        if not groups:
            self.warning("No valid group selected. No action is performed!")
            return

        self.set_groups(users, groups)

    def set_groups(self, users, groups):
        groups_string = self.get_groups_string(groups)
        for user in users:
            try:
                set_user_groups(user, groups)
            except Exception as error:
                self.error(
                    "Failed to add %s user to %s! %s", user.username,
                    groups_string, error
                )
            else:
                self.info(
                    "user %s added to %s", user.username,
                    groups_string, log=True
                )


@transaction.atomic
def set_user_groups(user, groups):
    for group in groups:
        user.groups.add(group)
