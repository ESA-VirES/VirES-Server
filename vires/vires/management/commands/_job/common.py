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

from vires.models import Job
from .._common import Subcommand, time_spec

STR_TO_STATUS = {label: status for status, label in Job.STATUS_CHOICES}


class JobSelectionSubcommand(Subcommand):
    """ Job selection subcommand. """

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "-u", "--user", dest="user",
            help="Filter jobs owned by the given user."
        )
        parser.add_argument(
            "-n", "--no-user", dest="nouser", action="store_true", default=False,
            help="Filter jobs not owned by any user."
        )
        parser.add_argument(
            "-s", "--status", choices=list(STR_TO_STATUS), action="append",
            help="Select jobs of the given status."
        )
        parser.add_argument(
            "--submitted-after", type=time_spec, required=False,
            help="Select jobs submitted after the given date."
        )
        parser.add_argument(
            "--submitted-before", type=time_spec, required=False,
            help="Select jobs submitted before the given date."
        )
        parser.add_argument(
            "--ended-after", type=time_spec, required=False,
            help="Select jobs which have been ended after the given date."
        )
        parser.add_argument(
            "--ended-before", type=time_spec, required=False,
            help="Select jobs which have been ended before the given date."
        )
        parser.add_argument(
            "--loose", dest="loose_jobs", action="store_true", default=None,
            help="Select jobs for which no actual WPS asynchronous job exists."
        )
        parser.add_argument(
            "--not-loose", dest="loose_jobs", action="store_false",
            help="Select only jobs which have a WPS asynchronous job."
        )
        parser.add_argument(
            "--active", dest="select_active", action="store_true",
            default=None, help="Select active WPS jobs."
        )
        parser.add_argument(
            "--not-active", dest="select_active", action="store_false",
            help="Select not active WPS jobs."
        )
        parser.add_argument(
            "--finished", dest="select_finished", action="store_true",
            default=None, help="Select finished WPS jobs."
        )
        parser.add_argument(
            "--not-finished", dest="select_finished", action="store_false",
            help="Select not finished WPS jobs."
        )
        parser.add_argument(
            "--with-response", dest="select_with_response", action="store_true",
            default=None, help="Select WPS jobs having an ExecuteResponse document."
        )
        parser.add_argument(
            "--without-response", dest="select_with_response", action="store_false",
            help="Select WPS jobs having no ExecuteResponse document."
        )

    def select_jobs(self, backend, **kwargs):
        """ Get list of matched jobs. """
        jobs = list(self._select_db_jobs(**kwargs))
        if self._is_backnend_query_needed(**kwargs):
            job_infos = dict(backend.list([job.identifier for job in jobs]))
            jobs = self._select_wps_jobs(jobs, job_infos, **kwargs)
        return jobs

    def select_jobs_with_info(self, backend, **kwargs):
        """ Get list of matched jobs and info dictionaries. """
        jobs = list(self._select_db_jobs(**kwargs))
        job_infos = dict(backend.list([job.identifier for job in jobs]))
        jobs = self._select_wps_jobs(jobs, job_infos, **kwargs)
        return [(job, job_infos.get(job.identifier)) for job in jobs]

    @staticmethod
    def _is_backnend_query_needed(**kwargs):
        """ Return True is the backend jobs need to be filtered. """
        backend_filters = [
            'loose_jobs', 'select_active', 'select_finished',
            'select_with_response',
        ]
        for key in backend_filters:
            if kwargs.get(key) is not None:
                return True
        return False

    def _select_wps_jobs(self, jobs, job_infos, **kwargs):

        def _select(condition, option1, option2):
            if condition is True:
                yield option1
            elif condition is False:
                yield option2

        predicates = []
        predicates.extend(_select(
            kwargs['loose_jobs'],
            lambda info: info is None,
            lambda info: info is not None,
        ))
        predicates.extend(_select(
            kwargs['select_active'],
            lambda info: info and info.get('is_active') is True,
            lambda info: info and info.get('is_active') is False,
        ))
        predicates.extend(_select(
            kwargs['select_finished'],
            lambda info: info and info.get('is_finished') is True,
            lambda info: info and info.get('is_finished') is False,
        ))
        predicates.extend(_select(
            kwargs['select_with_response'],
            lambda info: info and info.get('response_exists') is True,
            lambda info: info and info.get('response_exists') is False,
        ))

        def _filter_jobs():
            for job in jobs:
                job_info = job_infos.get(job.identifier)
                condition = True
                for predicate in predicates:
                    if not predicate(job_info):
                        condition = False
                        break
                if condition:
                    yield job

        return list(_filter_jobs()) if predicates else jobs

    def _select_db_jobs(self, **kwargs):
        """ Select products based on the CLI parameters. """
        query = Job.objects.prefetch_related("owner").order_by("created")

        query = self._select_jobs_by_id(query, **kwargs)

        if kwargs['user']:
            query = query.filter(owner__username=kwargs['user'])
        elif kwargs['nouser']:
            query = query.filter(owner__isnull=True)

        if kwargs['status']:
            query = query.filter(status__in=[
                STR_TO_STATUS[status] for status in set(kwargs['status'])
            ])

        if kwargs['submitted_after']:
            query = query.filter(created__gte=kwargs['submitted_after'])

        if kwargs['submitted_before']:
            query = query.filter(created__lt=kwargs['submitted_before'])

        if kwargs['ended_after']:
            query = query.filter(stopped__gte=kwargs['ended_after'])

        if kwargs['ended_before']:
            query = query.filter(stopped__lt=kwargs['ended_before'])

        return query

    def _select_jobs_by_id(self, query, **kwargs):
        identifiers = set(kwargs['identifier'])
        if identifiers:
            query = query.filter(identifier__in=identifiers)
        return query


class JobSelectionSubcommandProtected(JobSelectionSubcommand):
    """ Job selection subcommand requiring --all if no id given."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-a", "--all", dest="select_all", action="store_true", default=False,
            help="Select all jobs."
        )

    def _select_jobs_by_id(self, query, **kwargs):
        identifiers = set(kwargs['identifier'])
        if not kwargs['select_all']:
            query = query.filter(identifier__in=identifiers)
            if not identifiers:
                self.warning(
                    "No identifier selected and no job will be removed. "
                    "Use the --all option to remove all matched items."
                )
        return query
