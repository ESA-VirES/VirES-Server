#-------------------------------------------------------------------------------
#
#  Remove selected social providers
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
from traceback import print_exc
from allauth.socialaccount.models import SocialApp
from .._common import Subcommand


class RemoveProviderSubcommand(Subcommand):
    name = "remove"
    help = "Remove selected social network providers."

    def add_arguments(self, parser):
        parser.add_argument("providers", nargs="*", help="Selected providers.")

    def select_providers(self, query, **kwargs):
        providers = set(kwargs['providers'])
        query = query.filter(provider__in=providers)
        return query

    def handle(self, **kwargs):
        providers = self.select_providers(SocialApp.objects.all(), **kwargs)

        total_count = 0
        failed_count = 0
        removed_count = 0

        for provider in providers:
            name = provider.provider
            try:
                provider.delete()
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error("Failed to remove social provider %s! %s", name, error)
            else:
                removed_count += 1
                self.info("social provider %s removed", name, log=True)
            finally:
                total_count += 1

        if removed_count:
            self.info(
                "%d of %d social provider%s removed.",
                removed_count, total_count, "s" if total_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d social provider%s failed ",
                failed_count, total_count, "s" if total_count > 1 else ""
            )
