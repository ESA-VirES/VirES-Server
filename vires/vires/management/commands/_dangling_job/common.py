#-------------------------------------------------------------------------------
#
# product management - common utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020 EOX IT Services GmbH
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
# pylint: disable=abstract-method, no-self-use

from vires.util import unique
from vires.models import Job
from .._common import Subcommand

STR_TO_STATUS = {label: status for status, label in Job.STATUS_CHOICES}


class DanglingJobSelectionSubcommand(Subcommand):
    """ Dangling job selection subcommand. """

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "--active", dest="select_active", action="store_true",
            default=None, help="Select active jobs."
        )
        parser.add_argument(
            "--not-active", dest="select_active", action="store_false",
            help="Select not active jobs."
        )
        parser.add_argument(
            "--finished", dest="select_finished", action="store_true",
            default=None, help="Select finished jobs."
        )
        parser.add_argument(
            "--not-finished", dest="select_finished", action="store_false",
            help="Select not finished jobs."
        )
        parser.add_argument(
            "--with-response", dest="select_with_response", action="store_true",
            default=None, help="Select jobs having an ExecuteResponse document."
        )
        parser.add_argument(
            "--without-response", dest="select_with_response", action="store_false",
            help="Select jobs having no ExecuteResponse document."
        )

    def select_jobs(self, backend, **kwargs):
        """ Select products based on the CLI parameters. """
        selection = self._select_jobs_by_id(backend, **kwargs)

        select_active = kwargs['select_active']
        if select_active is not None:
            selection = [
                (id_, info) for id_, info in selection
                if info.get('is_active') == select_active
            ]

        select_finished = kwargs['select_finished']
        if select_finished is not None:
            selection = [
                (id_, info) for id_, info in selection
                if info.get('is_finished') == select_finished
            ]

        select_with_response = kwargs['select_with_response']
        if select_with_response is not None:
            selection = [
                (id_, info) for id_, info in selection
                if info.get('response_exists') == select_with_response
            ]

        return selection

    def _select_jobs_by_id(self, backend, **kwargs):
        identifiers = list(unique(kwargs['identifier'])) or None
        query = Job.objects
        if identifiers:
            query = query.filter(identifier__in=identifiers)
        job_info = backend.list(identifiers)
        job_set = set(query.values_list('identifier', flat=True))
        return [(id_, info) for id_, info in job_info if id_ not in job_set]


class DanglingJobSelectionSubcommandProtected(DanglingJobSelectionSubcommand):
    """ Job selection subcommand requiring --all if no id given."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all jobs."
        )

    def _select_jobs_by_id(self, backend, **kwargs):
        identifiers = list(unique(kwargs['identifier']))
        query = Job.objects
        if not kwargs['select_all']:
            query = query.filter(identifier__in=identifiers)
            if not identifiers:
                self.warning(
                    "No identifier selected and no job will be removed. "
                    "Use the --all option to remove all matched items."
                )
        else:
            identifiers = None
        job_info = backend.list(identifiers)
        job_set = set(query.values_list('identifier', flat=True))
        return [(id_, info) for id_, info in job_info if id_ not in job_set]
