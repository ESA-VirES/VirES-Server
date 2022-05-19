#-------------------------------------------------------------------------------
#
# Dump asynchronous WPS jobs in JSON format.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2022 EOX IT Services GmbH
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

import sys
import json
from argparse import RawTextHelpFormatter
from vires.time_util import format_datetime
from vires.models import Job
from vires.processes.remove_job import get_wps_async_backend
from .common import JobSelectionSubcommand
from .._common import JSON_OPTS

STATUS_TO_STR = dict(Job.STATUS_CHOICES)


class DumpJobSubcommand(JobSelectionSubcommand):
    name = "dump"
    help = "Dump asynchronous jobs in JSON format."

    description = (
        "Dump asynchronous jobs in JSON format.\n"
        "Meaning of the attributes:\n"
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

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        backend = get_wps_async_backend()

        data = [
            serialize_job(job, job_info or {})
            for job, job_info in self.select_jobs_with_info(backend, **kwargs)
        ]

        filename = kwargs["filename"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def serialize_job(job, info):
    return {
        "processId": job.process_id,
        "identifier": job.identifier,
        "owner": job.owner.username if job.owner else None,
        "status": STATUS_TO_STR[job.status],
        "submitted": format_datetime(job.created) or None,
        "started": format_datetime(job.started) or None,
        "ended": format_datetime(job.stopped) or None,
        "exists": bool(info),
        "hasResponse": info.get('response_exists', False),
        "finished": info.get('is_finished', False),
        "active": info.get('is_active', False),
        "responseUrl": job.response_url,
    }
