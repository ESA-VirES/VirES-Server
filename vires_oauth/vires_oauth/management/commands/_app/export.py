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
from oauth2_provider.models import Application
from vires_oauth.time_utils import datetime_to_string
from .._common import Subcommand, JSON_OPTS


class ExportAppSubcommand(Subcommand):
    name = "export"
    help = "Export registered OAuth applications in JSON format."

    def add_arguments(self, parser):
        parser.add_argument("apps", nargs="*", help="Selected applications.")
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        apps = self.select_apps(Application.objects.all(), **kwargs)

        data = [serialize_app(app) for app in apps]

        filename = kwargs['filename']
        with sys.stdout if filename == "-" else open(filename, "w") as file_:
            json.dump(data, file_, **JSON_OPTS)

    def select_apps(self, query, **kwargs):
        apps = kwargs['apps']
        if apps:
            query = (
                query.filter(name__in=apps) | query.filter(client_id__in=apps)
            )
        return query


def serialize_app(app):
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
