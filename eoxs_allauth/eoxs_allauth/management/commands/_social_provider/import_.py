#-------------------------------------------------------------------------------
#
# Load the social providers configuration
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
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from .._common import Subcommand


class ImportSocialProviderSubcommand(Subcommand):
    name = "import"
    help = "Load social network providers configuration in JSON format."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input JSON file-name. "
                "By default, the configuration is read from standard input."
            )
        )

    def handle(self, **kwargs):
        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.save_providers(json.load(file_), **kwargs)

    def save_providers(self, data, **kwargs):
        sites = list(Site.objects.filter(id=settings.SITE_ID))
        for item in data:
            name = item.get("provider")
            try:
                is_updated = save_provider(item, sites)
            except Exception as error:
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to create or update social provider %s! %s",
                    name, error
                )
            else:
                self.info(
                    "%s updated" if is_updated else "%s created",
                    name, log=True
                )


@transaction.atomic
def save_provider(item, sites):
    provider = item['provider']
    try:
        app = SocialApp.objects.get(provider=provider)
        id_updated = True
    except SocialApp.DoesNotExist:
        app = SocialApp(provider=provider)
        id_updated = False
    app.name = item.get('name')
    app.client_id = item.get('client_id')
    app.secret = item.get('secret')
    app.key = item.get('key') or ""
    app.save()
    app.sites.clear()
    for site in sites:
        app.sites.add(site)
    return id_updated
