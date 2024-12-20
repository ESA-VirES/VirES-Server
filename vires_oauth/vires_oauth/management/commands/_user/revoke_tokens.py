#-------------------------------------------------------------------------------
#
# User management - force revocation of all valid tokens
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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
from vires_oauth.management.api.user import remove_tokens, revoke_tokens
from .common import UserSelectionSubcommandProtected


class RevokeTokensSubcommand(UserSelectionSubcommandProtected):
    name = "revoke_tokens"
    help = "Force revocation of all valid OAuth/OIdC user tokens."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-d", "--delete", dest="remove_tokens", action="store_true",
            default=False, help="Force removal of the revoked tokens."
        )

    def handle(self, **kwargs):
        users = self.select_users(User.objects.all(), **kwargs)

        _revoke_tokens = (
            remove_tokens if kwargs["remove_tokens"] else revoke_tokens
        )

        for user in users:
            _revoke_tokens(user, logger=self)
