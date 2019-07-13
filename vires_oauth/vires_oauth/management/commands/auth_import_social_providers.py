#-------------------------------------------------------------------------------
#
# Import the social providers from a JSON file
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
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from ._common import ConsoleOutput


class Command(ConsoleOutput, BaseCommand):
    help = "Import social network providers configuration from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-",
            help="Input filename."
        )

    def handle(self, filename, **kwargs):

        with sys.stdin.buffer if filename == "-" else open(filename, "rb") as file_:
            data = json.load(file_)

        sites = list(Site.objects.filter(id=settings.SITE_ID))

        failed_count = 0
        created_count = 0
        updated_count = 0

        for item in data:
            name = item['provider']
            try:
                is_updated = save_social_provider(item, sites)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Failed to create or update social provider %s! %s",
                    name, error
                )
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info((
                    "Existing social provider %s updated." if is_updated else
                    "New social provider %s created."
                ), name)

        if created_count:
            self.info(
                "%d of %d provider%s updated.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d provider%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d provider%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )


@transaction.atomic
def save_social_provider(data, sites):
    provider = data['provider']
    try:
        app = SocialApp.objects.get(provider=provider)
        is_updated = True
    except SocialApp.DoesNotExist:
        app = SocialApp(provider=provider)
        is_updated = True

    for field in ['name', 'client_id', 'secret', 'key']:
        value = data.get('field')
        if value is not None:
            setattr(app, field, value)

    app.save()
    app.sites.set(sites)

    return is_updated
