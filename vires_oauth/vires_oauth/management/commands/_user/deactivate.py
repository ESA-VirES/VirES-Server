#-------------------------------------------------------------------------------
#
# User management - activate one or more inactive users
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2024 EOX IT Services GmbH
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

from django.contrib.auth.models import User
from vires_oauth.management.api.user import revoke_tokens
from .common import UserSelectionSubcommandProtected


class DeactivateUserSubcommand(UserSelectionSubcommandProtected):
    name = "deactivate"
    help = "Deactivate active users."

    def handle(self, **kwargs):
        users = self.select_users(User.objects.all(), **kwargs)

        for user in users:
            if user.is_active:
                user.is_active = False
                user.save()
                self.info("user %s deactivated", user.username, log=True)
                revoke_tokens(user, self)
            else:
                self.info("user %s is already inactive", user.username)
