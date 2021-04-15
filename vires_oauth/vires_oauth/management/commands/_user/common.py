#-------------------------------------------------------------------------------
#
# user management - common utilities
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

from django.contrib.postgres.aggregates import BoolAnd, BoolOr
from allauth.account.models import EmailAddress
from .._common import Subcommand, time_spec


class UserSelectionSubcommand(Subcommand):
    """ User selection subcommand. """

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="*")
        parser.add_argument(
            "--active", dest="is_active", action="store_true", default=None,
            help="Select activate users only."
        )
        parser.add_argument(
            "--inactive", dest="is_active", action="store_false", default=None,
            help="Select deactivated users."
        )
        parser.add_argument(
            "--no-login", action="store_true", default=False,
            help="Select user who joined but never logged in."
        )
        parser.add_argument(
            "--last-login-after", type=time_spec, required=False,
            help="Select user whose last logging occurred after the given date."
        )
        parser.add_argument(
            "--last-login-before", type=time_spec, required=False,
            help="Select user whose last logging occurred before the given date."
        )
        parser.add_argument(
            "--joined-after", type=time_spec, required=False,
            help="Select user whose last logging occurred after the given date."
        )
        parser.add_argument(
            "--joined-before", type=time_spec, required=False,
            help="Select user whose last logging occurred before the given date."
        )
        parser.add_argument(
            "--verified-primary-email",
            dest="has_verified_primary_email",
            action="store_true", default=None,
            help="Select users with verified primary e-mail."
        )
        parser.add_argument(
            "--not-verified-primary-email",
            dest="has_verified_primary_email",
            action="store_false", default=None,
            help="Select users with unverified primary e-mail."
        )
        parser.add_argument(
            "--verified-email", dest="has_verified_email",
            choices=("ANY", "ALL"), default=None,
            help="Select users with ANY|ALL verified e-mail(s)."
        )
        parser.add_argument(
            "--not-verified-email", dest="has_unverified_email",
            choices=("ANY", "ALL"), default=None,
            help="Select users with ANY|ALL unverified e-mail(s)."
        )

    def select_users(self, query, **kwargs):

        if kwargs['is_active'] is not None:
            query = query.filter(is_active=kwargs['is_active'])

        if kwargs['no_login']:
            query = query.filter(last_login=None)

        if kwargs['last_login_after']:
            query = query.filter(last_login__gte=kwargs['last_login_after'])

        if kwargs['last_login_before']:
            query = query.filter(last_login__lt=kwargs['last_login_before'])

        if kwargs['joined_after']:
            query = query.filter(date_joined__gte=kwargs['joined_after'])

        if kwargs['joined_before']:
            query = query.filter(date_joined__lt=kwargs['joined_before'])

        query = self._select_emails(query, **kwargs)
        query = self._select_users_by_id(query, **kwargs)

        return query

    def _select_emails(self, query, **kwargs):

        if kwargs['has_verified_primary_email'] is not None:
            query = query.filter(
                emailaddress__primary=True,
                emailaddress__verified=kwargs['has_verified_primary_email'],
            )

        if kwargs['has_verified_email'] or kwargs['has_unverified_email']:

            if kwargs['has_verified_email'] == 'ALL':
                aggregate, value = BoolAnd, True
            elif kwargs['has_verified_email'] == 'ANY':
                aggregate, value = BoolOr, True
            elif kwargs['has_unverified_email'] == 'ALL':
                aggregate, value = BoolOr, False
            elif kwargs['has_unverified_email'] == 'ANY':
                aggregate, value = BoolAnd, False

            query = query.filter(id__in=(
                EmailAddress.objects
                .annotate(aggregate=aggregate('verified'))
                .filter(aggregate=value)
                .values('user__id')
            ))

        return query

    def _select_users_by_id(self, query, **kwargs):
        usernames = kwargs['username']
        if usernames:
            query = query.filter(username__in=usernames)
        return query


class UserSelectionSubcommandProtected(UserSelectionSubcommand):
    """ User selection subcommand requiring --all if no id given."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all users."
        )

    def _select_users_by_id(self, query, **kwargs):
        usernames = kwargs['username']
        if usernames or not kwargs['select_all']:
            query = query.filter(username__in=usernames)
            if not usernames:
                self.warning(
                    "No username selected and no user will be modified. "
                    "Use the --all option to select all users."
                )
        return query
