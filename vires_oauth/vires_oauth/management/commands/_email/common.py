#-------------------------------------------------------------------------------
#
# e-mail management - common utilities
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
# pylint: disable=missing-docstring

from .._common import Subcommand #, time_spec


class EmailSelectionSubcommand(Subcommand):
    """ Email selection subcommand. """

    def add_arguments(self, parser):
        parser.add_argument("email", nargs="*")

        parser.add_argument(
            "-u", "--user", "--username", dest="users", action='append',
            help="Optional username filter. ",
        )

        parser.add_argument(
            "--primary", dest="is_primary", action="store_true", default=None,
            help="Select primary e-mails only."
        )
        parser.add_argument(
            "--not-primary", dest="is_primary", action="store_false", default=None,
            help="Select non-primary e-mails only."
        )

        parser.add_argument(
            "--verified", dest="is_verified", action="store_true", default=None,
            help="Select verified e-mails only."
        )
        parser.add_argument(
            "--not-verified", dest="is_verified", action="store_false", default=None,
            help="Select non-verified e-mails only."
        )

    def select_emails(self, query, **kwargs):

        if kwargs['is_primary'] is not None:
            query = query.filter(primary=kwargs['is_primary'])

        if kwargs['is_verified'] is not None:
            query = query.filter(verified=kwargs['is_verified'])

        if kwargs['users'] is not None:
            query = query.filter(user__username__in=kwargs['users'])

        query = self._select_emails_by_address(query, **kwargs)

        return query

    def _select_emails_by_address(self, query, **kwargs):
        emails = kwargs['email']
        if emails:
            query = query.filter(email__in=emails)
        return query


class EmailSelectionSubcommandProtected(EmailSelectionSubcommand):
    """ Email selection subcommand requiring --all if the selection possibly
    matches multiple e-mails.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all matched e-mails."
        )

    def _select_emails_by_address(self, query, **kwargs):
        emails = kwargs['email']
        select_all = (
            kwargs['select_all'] or (kwargs['users'] and kwargs['is_primary'])
        )
        if emails or not select_all:
            query = query.filter(email__in=emails)
            if not emails:
                self.warning(
                    "The selection is ambiguous and no e-mail will be modified. "
                    "Use the --all option to select all matched e-mails."
                )
        return query
