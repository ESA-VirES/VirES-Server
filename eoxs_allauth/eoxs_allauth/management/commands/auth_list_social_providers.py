#-------------------------------------------------------------------------------
#
# Dump the social providers configuration
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
from optparse import make_option
from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn,
)

JSON_OPTS = {
    'sort_keys': False,
    'indent': 2,
    'separators': (',', ': '),
}


class Command(CommandOutputMixIn, BaseCommand):
    args = "<provider> [<provider> ...]"
    help = "Dump social network providers configuration in JSON format."
    option_list = BaseCommand.option_list + (
        make_option(
            "-f", "--file", dest="filename", default="-",
            help="Output filename."
        ),
    )

    def handle(self, *args, **kwargs):
        providers = args
        filename = kwargs['filename']

        # select user profile
        query = SocialApp.objects
        if not providers:
            query = query.all()
        else:
            query = query.filter(provider__in=providers)

        data = [{
            "provider": app.provider,
            "name": app.name,
            "client_id": app.client_id,
            "secret": app.secret,
            "key": app.key,
        } for app in query]

        with sys.stdout if filename == "-" else open(filename, "w") as file_:
            json.dump(data, file_, **JSON_OPTS)
