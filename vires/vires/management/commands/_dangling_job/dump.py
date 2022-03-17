#-------------------------------------------------------------------------------
#
# Dump asynchronous WPS jobs without any Job DB record in JSON format.
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
from vires.processes.remove_job import get_wps_async_backend
from .common import DanglingJobSelectionSubcommand
from .._common import JSON_OPTS


class DumpDanglingJobSubcommand(DanglingJobSelectionSubcommand):
    name = "dump"
    help = "Dump asynchronous jobs without any DB record in JSON format."

    description = (
        "Dump asynchronous jobs without any DB record in JSON format.\n"
        "Meaning of the job attributes:\n"
        "  identifier  job unique identifier\n"
        "  hasResponse job ExecuteResponse XML document exists (WPS backend)\n"
        "  finished    job has been terminated (WPS backend)\n"
        "  active      job is active, i.e., the temporary context exists (WPS backend)\n"
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
            serialize_dangling_job(identifier, info)
            for identifier, info in self.select_jobs(backend, **kwargs)
        ]

        filename = kwargs["filename"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def serialize_dangling_job(identifier, info):
    return {
        "identifier": identifier,
        "hasResponse": info.get('response_exists', False),
        "finished": info.get('is_finished', False),
        "active": info.get('is_active', False),
    }
