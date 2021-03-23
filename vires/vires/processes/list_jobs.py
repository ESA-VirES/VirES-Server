#-------------------------------------------------------------------------------
#
# WPS process listing all asynchronous jobs of a user.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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
# pylint: disable=no-self-use,too-few-public-methods

from eoxserver.services.ows.wps.parameters import (
    RequestParameter, ComplexData, FormatJSON, CDObject,
)
from vires.models import Job
from vires.access_util import get_user
from vires.time_util import format_datetime
from vires.processes.base import WPSProcess

STATUS_TO_STRING = dict(Job.STATUS_CHOICES)


class ListJobs(WPSProcess):
    """ This utility process lists all asynchronous WPS jobs owned by
    the current user.
    The jobs are grouped by the process identifier and ordered by the creation
    time.
    """
    identifier = "listJobs"
    metadata = {}
    profiles = ["vires-util"]

    inputs = WPSProcess.inputs + [
        ('user', RequestParameter(get_user)),
    ]

    outputs = [
        ("job_list", ComplexData(
            "job_list", title="List of owned WPS Jobs.",
            formats=[FormatJSON()],
        )),
    ]

    def execute(self, user, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        owner = user if user and user.is_authenticated else None
        job_list = {}
        for job in Job.objects.filter(owner=owner).order_by("created"):
            job_list.setdefault(job.process_id, []).append({
                "id": str(job.identifier),
                "url": str(job.response_url),
                "created": format_datetime(job.created),
                "started": format_datetime(job.started),
                "stopped": format_datetime(job.stopped),
                "status": STATUS_TO_STRING[job.status],
            })

        access_logger.info("request:")

        return CDObject(
            job_list, format=FormatJSON(), filename="job_list.json",
            **kwargs['job_list']
        )
