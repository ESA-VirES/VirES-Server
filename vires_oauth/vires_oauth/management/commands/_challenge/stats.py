#-------------------------------------------------------------------------------
#
# Altcha challenge management - get statistics
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


class GetChallengeStatsSubcommand(Subcommand):
    name = "stats"
    help = "Get challenges statistics."

    def handle(self, **kwargs):
        del kwargs

        now_ = now()

        total = 0
        valid = 0
        expired = 0
        used = 0

        for item in Challenge.objects.all():
            total += 1
            if item.used:
                used += 1
            elif item.expires is not None and item.expires <= now_:
                expired += 1
            else:
                valid += 1

        print(f"Valid:    {valid}")
        print(f"Used:     {used}")
        print(f"Expired:  {expired}")
        print(f"Total:    {total}")
