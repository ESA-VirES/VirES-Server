#-------------------------------------------------------------------------------
#
# WPS process listing all asynchronous jobs of a user.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=no-self-use,missing-docstring, too-few-public-methods

from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.parameters import (
    RequestParameter, ComplexData, FormatJSON, CDObject,
)
from vires.models import Job

STATUS_TO_STRING = dict(Job.STATUS_CHOICES)


class ListJobs(Component):
    """ This utility process lists all asynchronous WPS jobs owned by
    the current user.
    The jobs are grouped by the process identifier and ordered by the creation
    time.
    """
    implements(ProcessInterface)

    identifier = "listJobs"
    metadata = {}
    profiles = ["vires-util"]

    inputs = [
        ('user', RequestParameter(lambda request: request.user)),
    ]

    outputs = [
        ("job_list", ComplexData(
            "job_list", title="List of owned WPS Jobs.",
            formats=[FormatJSON()],
        )),
    ]

    def execute(self, user, **kwargs):
        owner = user if user.is_authenticated() else None
        job_list = {}
        for job in Job.objects.filter(owner=owner).order_by("created"):
            job_list.setdefault(job.process_id, []).append({
                "id": str(job.identifier),
                "url": str(job.response_url),
                "created": job.created.isoformat("T"),
                "started": job.started.isoformat("T") if job.started else None,
                "stopped": job.stopped.isoformat("T") if job.stopped else None,
                "status": STATUS_TO_STRING[job.status],
            })
        return CDObject(
            job_list, format=FormatJSON(), filename="job_list.json",
            **kwargs['job_list']
        )
