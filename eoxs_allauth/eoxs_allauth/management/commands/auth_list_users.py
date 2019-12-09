#-------------------------------------------------------------------------------
#
# User management - dump users' info
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

import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import UserProfile
from ._common import ConsoleOutput, datetime_to_string


class Command(ConsoleOutput, BaseCommand):

    help = (
        "Print information about the AllAuth users. The users are selected "
        "either by the provided user names (no user name - no output) or "
        "by the '--all' option. "
        "By default, only the user names are listed. A brief summary for each "
        "user can be obtained by '--info' option."
    )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("username", nargs="*")
        parser.add_argument(
            "--info", dest="info_dump", action="store_true", default=False,
            help="Verbose text output."
        )
        parser.add_argument(
            "-f", "--file-name", dest="file", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, *args, **kwargs):
        usernames = kwargs['username']
        query = User.objects
        if not usernames:
            query = query.all()
        else:
            query = query.filter(username__in=usernames)
        # select output class
        if kwargs["info_dump"]:
            output = VerboseOutput
        else:
            output = BriefOutput
        # output
        fout = sys.stdout if kwargs["file"] == "-" else open(kwargs["file"])
        with fout:
            fout.write(output.start)
            dlm = ""
            for item in query:
                fout.write(dlm)
                fout.write(output.to_str(item))
                dlm = output.delimiter
            fout.write(output.stop)


class BriefOutput(object):
    start = ""
    stop = ""
    delimiter = ""

    @staticmethod
    def to_str(user):
        return user.username + "\n"


class VerboseOutput(object):
    start = ""
    stop = ""
    delimiter = "\n"

    @classmethod
    def to_str(cls, user):
        out = ["user: %s" % user.username]
        out.extend(
            "%14s: %s" % (key, value)
            for key, value in cls.extract_user_profile(user)
        )
        out.append("")
        return ("\n".join(out)).encode('utf8')

    @classmethod
    def get_profile(cls, user):
        try:
            return user.userprofile
        except UserProfile.DoesNotExist:
            return None

    @classmethod
    def extract_user_profile(cls, user):
        social_accounts = list(user.socialaccount_set.all())
        emails = list(user.emailaddress_set.all())

        dates_joined = [
            item.date_joined for item in social_accounts
            if item.date_joined is not None
        ]
        if user.date_joined is not None:
            dates_joined.append(user.date_joined)
        date_joined = max(dates_joined) if dates_joined else None

        last_logins = [
            item.last_login for item in social_accounts
            if item.last_login is not None
        ]
        if user.last_login is not None:
            last_logins.append(user.last_login)
        last_login = max(last_logins) if last_logins else None

        providers = [item.provider for item in social_accounts]
        primary_emails = [item.email for item in emails if item.primary]
        other_emails = [item.email for item in emails if not item.primary]
        if user.email and user.email not in primary_emails:
            primary_emails = [user.email] + primary_emails

        profile = cls.get_profile(user) or ""

        yield ("is active", user.is_active)
        yield ("first name", user.first_name)
        yield ("last name", user.last_name)
        yield ("title", profile and profile.title)
        yield ("institution", profile and profile.institution)
        yield ("country", profile and profile.country)
        yield ("study area", profile and profile.study_area)
        yield ("primary email", ", ".join(primary_emails))
        yield ("other emails", ", ".join(other_emails))
        yield ("social accts.", ", ".join(providers))
        yield ("date joined", datetime_to_string(date_joined))
        yield ("last login", datetime_to_string(last_login))
