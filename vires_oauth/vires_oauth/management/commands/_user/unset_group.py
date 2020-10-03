#-------------------------------------------------------------------------------
#
# User management - remove users from one or more user groups
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
from .set_group import SelectGroupMixIn


class UnsetUserGroupSubcommand(UserSelectionSubcommandProtected, SelectGroupMixIn):
    name = "unset_group"
    help = "Remove users from one or more groups."

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

        self.unset_groups(users, groups)

    def unset_groups(self, users, groups):
        groups_string = self.get_groups_string(groups)
        for user in users:
            try:
                unset_user_groups(user, groups)
            except Exception as error:
                self.error(
                    "Failed to remove %s user from %s! %s", user.username,
                    groups_string, error
                )
            else:
                self.info(
                    "user %s removed from %s", user.username,
                    groups_string, log=True
                )


@transaction.atomic
def unset_user_groups(user, groups):
    for group in groups:
        user.groups.remove(group)
