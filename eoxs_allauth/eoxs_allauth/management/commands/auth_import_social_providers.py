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
from django.db import transaction
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn,
)


class Command(CommandOutputMixIn, BaseCommand):

    help = "Load social network providers configuration in JSON format."

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "-f", "--file", dest="filename", default="-",
            help="Input filename."
        )

    def handle(self, *args, **kwargs):
        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            data = json.load(file_)

        sites = list(Site.objects.filter(id=settings.SITE_ID))
        with transaction.atomic():
            for item in data:
                try:
                    app = SocialApp.objects.get(provider=item.get('provider'))
                except SocialApp.DoesNotExist:
                    app = SocialApp()
                app.name = item.get('name')
                app.provider = item.get('provider')
                app.client_id = item.get('client_id')
                app.secret = item.get('secret')
                app.key = item.get('key') or ""
                app.save()
                app.sites.clear()
                for site in sites:
                    app.sites.add(site)
