#-------------------------------------------------------------------------------
#
# Set current site.
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

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import CommandError
from .._common import Subcommand


class SetSiteSubcommand(Subcommand):
    name = "set"
    help = "Set current site parameters."

    def add_arguments(self, parser):
        parser.add_argument(
            "-n", "--name", dest="name", default=None, help="Site name."
        )
        parser.add_argument(
            "-d", "--domain", dest="domain", default=None, help="Site domain."
        )

    def handle(self, **kwargs):

        name = kwargs['name']
        domain = kwargs['domain']

        try:
            site = Site.objects.get(id=settings.SITE_ID)
        except Site.DoesNotExist:
            site = Site()
            site.id = settings.SITE_ID
            if not name or not domain:
                raise CommandError(
                    "Both name and domain must be specified for a new site!"
                )

        if name:
            site.name = name

        if domain:
            site.domain = domain

        if name or domain:
            site.save()
