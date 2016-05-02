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
import json
from collections import OrderedDict
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, #nested_commit_on_success
)
from ...models import UserProfile

JSON_OPTS = {'sort_keys': False, 'indent': 2, 'separators': (',', ': ')}


class Command(CommandOutputMixIn, BaseCommand):
    args = "<username> [<username> ...]"
    help = (
        "Print information about the AllAuth users. The users are selected "
        "either by the provided user names (no user name - no output) or "
        "by the '--all' option. "
        "By default, only the user names are listed. A brief summary for each "
        "user can be obtained by '--info' option. The '--json' option produces "
        "full user profile dump in JSON format."
    )
    option_list = BaseCommand.option_list + (
        make_option(
            "-a", "--all", dest="all_users", action="store_true", default=False,
            help="Select all users."
        ),
        make_option(
            "--info", dest="info_dump", action="store_true", default=False,
            help="Verbose text output."
        ),
        make_option(
            "--json", dest="json_dump", action="store_true", default=False,
            help="JSON dump."
        ),
        make_option(
            "-f", "--file-name", dest="file", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
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
        # select output class
        if kwargs["json_dump"]:
            output = JSONOutput
        elif kwargs["info_dump"]:
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


class BriefOutput(object):
    start = ""
    stop = ""
    delimiter = ""

    @staticmethod
    def to_str(profile):
        return profile.user.username + "\n"


class VerboseOutput(object):
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
        return ("\n".join(out)).encode('utf8')

    @classmethod
    def extract_user_profile(cls, profile):
        social_accounts = list(profile.user.socialaccount_set.all())
        emails = list(profile.user.emailaddress_set.all())
        date_joined = min(profile.user.date_joined, min(
            item.date_joined for item in social_accounts
        ))
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


class JSONOutput(object):
    start = "["
    stop = "]\n"
    delimiter = ",\n"

    @classmethod
    def to_str(cls, profile):
        return json.dumps(
            OrderedDict(cls.extract_user_profile(profile)), **JSON_OPTS
        )

    @classmethod
    def extract_user_profile(cls, profile):
        for item in cls.extract_user(profile.user):
            yield item
        if profile.title:
            yield ("title", profile.title)
        if profile.institution:
            yield ("institution", profile.institution)
        if profile.country:
            yield ("country", str(profile.country))
        if profile.study_area:
            yield ("study_area", profile.study_area)
        if profile.executive_summary:
            yield ("executive_summary", profile.executive_summary)

    @classmethod
    def extract_user(cls, user):
        yield ("username", user.username)
        if user.password:
            yield ("password", user.password)
        yield ("is_active", user.is_active)
        yield ("date_joined", datetime_to_string(user.date_joined))
        yield ("last_login", datetime_to_string(user.last_login))
        if user.first_name:
            yield ("first_name", user.first_name)
        if user.last_name:
            yield ("last_name", user.last_name)
        #if user.email: # copy of the primary e-mail
        #    yield ("email", user.email)
        yield ("emails", [
            OrderedDict(cls.extract_email_address(item))
            for item in user.emailaddress_set.all()
        ])
        yield ("social_accounts", [
            OrderedDict(cls.extract_social_account(item))
            for item in user.socialaccount_set.all()
        ])

    @classmethod
    def extract_email_address(cls, emailaddress):
        yield ("email", emailaddress.email)
        yield ("verified", emailaddress.verified)
        if emailaddress.primary:
            yield ("primary", emailaddress.primary)

    @classmethod
    def extract_social_account(cls, socialaccount):
        #yield ("email", emailaddress.email)
        #yield ("verified", emailaddress.verified)
        #if emailaddress.primary:
        #    yield ("primary", emailaddress.primary)
        yield ("uid", socialaccount.uid)
        yield ("provider", socialaccount.provider)
        yield ("date_joined", datetime_to_string(socialaccount.date_joined))
        yield ("last_login", datetime_to_string(socialaccount.last_login))
        if socialaccount.extra_data:
            yield ("extra_data", socialaccount.extra_data)

def datetime_to_string(dtobj):
    return dtobj if dtobj is None else dtobj.isoformat('T')
