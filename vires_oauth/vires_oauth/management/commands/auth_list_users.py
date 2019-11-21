#-------------------------------------------------------------------------------
#
# User management - print information about the users
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

import sys
from collections import OrderedDict
from django.core.management.base import BaseCommand
from ...models import UserProfile, Permission
from ._common import ConsoleOutput, datetime_to_string


class Command(ConsoleOutput, BaseCommand):
    help = (
        "Print information about the users. The users can be selected "
        "by the provided user names. By default, all users are printed."
        "By default, only the user names are listed. A brief summary for each "
        "user can be obtained by '--info' option."
    )

    def add_arguments(self, parser):
        parser.add_argument("users", nargs="*", help="Selected users.")
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

    def handle(self, users, **kwargs):
        # select user profile
        qset = UserProfile.objects.select_related('user')
        if not users:
            qset = qset.all()
        else:
            qset = qset.filter(user__username__in=users)
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
            for item in qset:
                fout.write(dlm)
                fout.write(output.to_str(item))
                dlm = output.delimiter
            fout.write(output.stop)


class BriefOutput():
    start = ""
    stop = ""
    delimiter = ""

    @staticmethod
    def to_str(profile):
        return profile.user.username + "\n"


class VerboseOutput():
    start = ""
    stop = ""
    delimiter = "\n"

    @classmethod
    def to_str(cls, profile):
        out = ["user: %s" % profile.user.username]
        out.extend(
            "%14s: %s" % (key, value)
            for key, value in cls.extract_user_profile(profile)
        )
        out.append("")
        return "\n".join(out)

    @classmethod
    def extract_user_profile(cls, profile):
        social_accounts = list(profile.user.socialaccount_set.all())
        emails = list(profile.user.emailaddress_set.all())

        dates_joined = [
            item.date_joined for item in social_accounts
            if item.date_joined is not None
        ]
        if profile.user.date_joined is not None:
            dates_joined.append(profile.user.date_joined)
        date_joined = max(dates_joined) if dates_joined else None

        last_logins = [
            item.last_login for item in social_accounts
            if item.last_login is not None
        ]
        if profile.user.last_login is not None:
            last_logins.append(profile.user.last_login)
        last_login = max(last_logins) if last_logins else None

        providers = [item.provider for item in social_accounts]
        primary_emails = [item.email for item in emails if item.primary]
        other_emails = [item.email for item in emails if not item.primary]
        if profile.user.email and profile.user.email not in primary_emails:
            primary_emails = [profile.user.email] + primary_emails

        yield ("groups", ", ".join(
            group.name for group in profile.user.groups.all()
        ))

        yield ("permissions", ", ".join(
            list(Permission.get_user_permissions(profile.user))
        ))
        yield ("is active", profile.user.is_active)
        yield ("first name", profile.user.first_name)
        yield ("last name", profile.user.last_name)
        yield ("title", profile.title)
        yield ("institution", profile.institution)
        yield ("country", profile.country)
        yield ("study area", profile.study_area)
        yield ("primary email", ", ".join(primary_emails))
        yield ("other emails", ", ".join(other_emails))
        yield ("social accts.", ", ".join(providers))
        yield ("date joined", datetime_to_string(date_joined))
        yield ("last login", datetime_to_string(last_login))
        yield (
            "consented service terms version",
            profile.consented_service_terms_version
        )
