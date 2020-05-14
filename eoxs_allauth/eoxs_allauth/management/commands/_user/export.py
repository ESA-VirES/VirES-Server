#-------------------------------------------------------------------------------
#
# Export users in JSON format.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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

import sys
import json
import base64
from functools import partial
from collections import OrderedDict
from django.contrib.auth.models import User
from eoxs_allauth.models import UserProfile
from eoxs_allauth.utils import datetime_to_string
from .._common import JSON_OPTS
from .common import UserSelectionSubcommand


class ExportUserSubcommand(UserSelectionSubcommand):
    name = "export"
    help = "Export users in JSON format."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file-name", dest="file", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        users = self.select_users(User.objects.all(), **kwargs)

        data = [serialize_user(user) for user in users]

        filename = kwargs["file"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def strip_blanks(func):
    """ Decorator removing blank fields from the serialized objects """
    def _strip_blanks_(*args, **kwargs):
        return OrderedDict(
            (key, value) for key, value in func(*args, **kwargs).items()
            if value not in (None, "")
        )
    return _strip_blanks_


@strip_blanks
def serialize_user_profile(object_):
    return OrderedDict([
        ("title", object_.title),
        ("institution", object_.institution),
        ("country", object_.country.code),
        ("study_area", object_.study_area),
        ("executive_summary", object_.executive_summary),
    ])


@strip_blanks
def serialize_user(object_):
    try:
        user_profile = object_.userprofile
    except UserProfile.DoesNotExist:
        user_profile = None

    return OrderedDict([
        ("username", object_.username),
        ("password", object_.password),
        ("is_active", object_.is_active),
        ("date_joined", datetime_to_string(object_.date_joined)),
        ("last_login", datetime_to_string(object_.last_login)),
        ("first_name", object_.first_name),
        ("last_name", object_.last_name),
        ("email", object_.email), # copy of the primary e-mail
        (
            "user_profile",
            serialize_user_profile(user_profile) if user_profile else None
        ),
        (
            "email_addresses",
            serialize_email_addresses(object_.emailaddress_set.all())
        ),
        (
            "social_accounts",
            serialize_social_accounts(object_.socialaccount_set.all())
        ),
        (
            "access_tokens",
            serialize_access_tokens(object_.tokens.all())
        ),
    ])


@strip_blanks
def serialize_email_address(object_):
    return OrderedDict([
        ("email", object_.email),
        ("verified", object_.verified),
        ("primary", object_.primary),
    ])


@strip_blanks
def serialize_social_account(object_):
    return OrderedDict([
        ("uid", object_.uid),
        ("provider", object_.provider),
        ("date_joined", datetime_to_string(object_.date_joined)),
        ("last_login", datetime_to_string(object_.last_login)),
        ("extra_data", object_.extra_data),
        ("provider", object_.provider),
    ])


@strip_blanks
def serialize_access_token(object_):
    return OrderedDict([
        ("identifier", object_.identifier),
        ("token_sha256", binary_to_base64(object_.token_sha256)),
        ("purpose", object_.purpose),
        ("expires", object_.expires and datetime_to_string(object_.expires)),
        ("created", datetime_to_string(object_.created)),
    ])


def serialize_list(funct, objects):
    return [funct(object_) for object_ in objects]


def binary_to_base64(data):
    return base64.urlsafe_b64encode(data).decode('ascii')

serialize_email_addresses = partial(serialize_list, serialize_email_address)
serialize_social_accounts = partial(serialize_list, serialize_social_account)
serialize_access_tokens = partial(serialize_list, serialize_access_token)
