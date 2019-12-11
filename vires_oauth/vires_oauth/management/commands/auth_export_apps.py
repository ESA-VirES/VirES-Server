#-------------------------------------------------------------------------------
#
# Export registered application in JSON format.
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
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application
from ._common import ConsoleOutput, datetime_to_string, JSON_OPTS


class Command(ConsoleOutput, BaseCommand):
    help = "Export registered applications in JSON format."

    def add_arguments(self, parser):
        parser.add_argument("apps", nargs="*", help="Selected applications.")
        parser.add_argument(
            "-f", "--file", dest="filename", default="-",
            help="Output filename."
        )

    def handle(self, apps, filename, **kwargs):
        query = Application.objects
        if not apps:
            query = query.all()
        else:
            query = (
                query.filter(name__in=apps) | query.filter(client_id__in=apps)
            )

        data = [extract_app(app) for app in query]

        with sys.stdout if filename == "-" else open(filename, "w") as file_:
            json.dump(data, file_, **JSON_OPTS)


def extract_app(app):
    return {
        "owner": None if app.user is None else app.user.username,
        "name": app.name,
        "client_id": app.client_id,
        "client_secret": app.client_secret,
        "client_type": app.client_type,
        "authorization_grant_type": app.authorization_grant_type,
        "skip_authorization": app.skip_authorization,
        "created": datetime_to_string(app.created),
        "updated": datetime_to_string(app.updated),
        "redirect_uris": (app.redirect_uris or "").split(),
    }
