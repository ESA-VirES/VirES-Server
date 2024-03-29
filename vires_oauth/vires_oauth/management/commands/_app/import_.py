#-------------------------------------------------------------------------------
#
# Import and registered OAuth applications from a JSON file
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
# pylint: disable=missing-docstring, too-few-public-methods

import sys
import json
from traceback import print_exc
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.contrib.auth.models import User
from oauth2_provider.models import get_application_model
from .._common import Subcommand


class ImportAppSubcommand(Subcommand):
    name = "import"
    help = "Import and registered OAuth applications from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):

        filename = kwargs['filename']
        with sys.stdin.buffer if filename == "-" else open(filename, "rb") as file_:
            data = json.load(file_)

        failed_count = 0
        created_count = 0
        updated_count = 0

        for item in data:
            name = item['client_id']
            if item.get('name'):
                name += " (%s)" % item['name']

            try:
                is_updated = save_app(item)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to create or update the app %s! %s",
                    name, error
                )
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info(
                    "app %s updated" if is_updated else
                    "app %s created", name, log=True
                )

        if created_count:
            self.info(
                "%d of %d app%s updated.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d app%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d app%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )


KEY_PARSERS = {
    "created": parse_datetime,
    "updated": parse_datetime,
    "redirect_uris": lambda uris: " ".join(str(uri) for uri in uris),
    "skip_authorization": bool,
}

APP_KEYS = [
    "name",
    "client_secret",
    "client_type",
    "authorization_grant_type",
    "skip_authorization",
    "created",
    "updated",
    "redirect_uris",
]


@transaction.atomic
def save_app(item):
    # NOTE: The application model detects if the client secret is hashed or
    #       plain text. Plain text secrets are hashed on save. Hashed secretes
    #       are saved without modification.
    client_id = item['client_id']

    model = get_application_model()
    try:
        app = model.objects.get(client_id=client_id)
        is_updated = True
    except model.DoesNotExist:
        app = model(client_id=client_id)
        is_updated = False

    if 'owner' in item:
        app.user = get_user(item['owner'])

    for key in APP_KEYS:
        value = item.get(key)
        if value is not None:
            setattr(app, key, KEY_PARSERS.get(key, str)(value))

    app.save()

    return is_updated


def get_user(username):
    return None if username is None else User.objects.get(username=username)
