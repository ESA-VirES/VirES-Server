#-------------------------------------------------------------------------------
#
# List asynchronous WPS jobs without any Job DB record.
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
from vires.processes.remove_job import get_wps_async_backend
from .common import DanglingJobSelectionSubcommand


class InfoDanglingJobSubcommand(DanglingJobSelectionSubcommand):
    name = "info"
    help = (
        "Print detailed information about the asynchronous jobs without any "
        "DB record."
    )

    description = (
        "Print detailed information about the asynchronous jobs without any "
        "DB record in CSV format.\n"
        "Meaning of the table columns:\n"
        "  identifier  job unique identifier\n"
        "  hasResponse job ExecuteResponse XML document exists (WPS backend)\n"
        "  finished    job has been terminated (WPS backend)\n"
        "  active      job is active, i.e., the temporary context exists (WPS backend)\n"
    )
    formatter_class = RawTextHelpFormatter

    def handle(self, **kwargs):
        backend = get_wps_async_backend()

        print_raw_job_header()
        for identifier, info in self.select_jobs(backend, **kwargs):
            print_raw_job(identifier, info)


def print_raw_job_header():
    print(",".join([
        "identifier",
        "hasResponse",
        "finished",
        "active",
    ]))

def print_raw_job(identifier, info):
    print(",".join([
        identifier,
        str(info.get('response_exists', False)),
        str(info.get('is_finished', False)),
        str(info.get('is_active', False)),
    ]))
