#-------------------------------------------------------------------------------
#
# List asynchronous WPS jobs
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
# pylint: disable=missing-docstring

from argparse import RawTextHelpFormatter
from vires.time_util import format_datetime
from vires.models import Job
from vires.processes.remove_job import get_wps_async_backend
from .common import JobSelectionSubcommand

STATUS_TO_STR = dict(Job.STATUS_CHOICES)


class InfoJobSubcommand(JobSelectionSubcommand):
    name = "info"
    help = "Print detailed information about the asynchronous jobs."

    description = (
        "Print detailed information about the asynchronous jobs in CSV format.\n"
        "Meaning of the table columns:\n"
        "  processId   WPS process identifier\n"
        "  identifier  job unique identifier\n"
        "  owner       username of the job owner\n"
        "  status      job status (DB record)\n"
        "  submitted   job creation timestamp (DB record)\n"
        "  started     job execution start timetamp (DB record)\n"
        "  ended       job execution end timestamp (DB record)\n"
        "  exists      job physically exists (WPS backend)\n"
        "  hasResponse job ExecuteResponse XML document exists (WPS backend)\n"
        "  finished    job has been terminated (WPS backend)\n"
        "  active      job is active, i.e., the temporary context exists (WPS backend)\n"
        "  responseUrl the URL if the ExecuteResponse XML document\n"
    )
    formatter_class = RawTextHelpFormatter

    def handle(self, **kwargs):
        backend = get_wps_async_backend()

        print_db_job_header()
        for job, job_info in self.select_jobs_with_info(backend, **kwargs):
            print_db_job(job, job_info or {})


def print_db_job_header():
    print(",".join([
        "processId",
        "identifier",
        "owner",
        "status",
        "submitted",
        "started",
        "ended",
        "exists",
        "hasResponse",
        "finished",
        "active",
        "responseUrl"
    ]))

def print_db_job(job, info):
    print(",".join([
        job.process_id,
        job.identifier,
        job.owner.username if job.owner else "",
        STATUS_TO_STR[job.status],
        format_datetime(job.created) or "",
        format_datetime(job.started) or "",
        format_datetime(job.stopped) or "",
        str(bool(info)),
        str(info.get('response_exists', False)),
        str(info.get('is_finished', False)),
        str(info.get('is_active', False)),
        job.response_url,
    ]))
