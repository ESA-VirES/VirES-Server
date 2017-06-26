#-------------------------------------------------------------------------------
#
# Project: EOxServer <http://eoxserver.org>
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

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from eoxserver.resources.coverages.management.commands import CommandOutputMixIn
from vires.orbit_counter import update_orbit_counter_file
from vires.management.commands.vires_update_aux import update


class Command(CommandOutputMixIn, BaseCommand):
    """ Update Swarm orbit counter files from the given source. """
    option_list = BaseCommand.option_list + (
        make_option(
            "-a", "--alpha-url", "--alpha-filename", "--alpha",
            dest="filename_a", action="store", default=None,
            help="Alpha orbit number counter source (-, file-name, or URL)."
        ),
        make_option(
            "-b", "--beta-url", "--beta-filename", "--beta",
            dest="filename_b", action="store", default=None,
            help="Beta orbit number number source (-, file-name, or URL)."
        ),
        make_option(
            "-c", "--charlie-url", "--charlie-filename", "--charlie",
            dest="filename_c", action="store", default=None,
            help="Charlie orbit number number source (-, file-name, or URL)."
        ),
    )

    options = [
        (
            "filename_a", settings.VIRES_ORBIT_COUNTER_DB['A'],
            "Swarm A orbit counter"
        ),
        (
            "filename_b", settings.VIRES_ORBIT_COUNTER_DB['B'],
            "Swarm B orbit counter"
        ),
        (
            "filename_c", settings.VIRES_ORBIT_COUNTER_DB['C'],
            "Swarm C orbit counter"
        ),
    ]

    def handle(self, *args, **kwargs):
        for opt_name, destination, label in self.options:
            if kwargs[opt_name] is not None:
                update(
                    kwargs[opt_name], destination,
                    update_orbit_counter_file, label
                )
