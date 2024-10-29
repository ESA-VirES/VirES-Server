#-------------------------------------------------------------------------------
#
# Altcha challenge management - clear expired and used tokens
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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

from django.db.models import Q
from vires_oauth.models import Challenge
from vires_oauth.time_utils import now
from .._common import Subcommand, time_spec


class ClearChallengeSubcommand(Subcommand):
    name = "clear"
    help = "Clear stored challenges."

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove-older-than", type=time_spec, required=False,
            help="Remove challenges older than the given date."
        )

    def handle(self, **kwargs):
        challenges = self.select_challenges(Challenge.objects.all(), **kwargs)
        challenges.delete()

    def select_challenges(self, query, **kwargs):

        complex_query = (
            Q(used=True) |
            Q(expires__isnull=False, expires__lte=now())
        )

        if kwargs["remove_older_than"]:
            complex_query = (
                complex_query |
                Q(created__lte=kwargs["remove_older_than"])
            )

        return query.filter(complex_query)
