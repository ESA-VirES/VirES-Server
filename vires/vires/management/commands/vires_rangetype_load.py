#-------------------------------------------------------------------------------
#
# Initialize VirES range types.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2011 EOX IT Services GmbH
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

from optparse import make_option
from django.core.management.base import BaseCommand
from eoxserver.resources.coverages.management.commands import (
    eoxs_rangetype_load
)
from vires.data import RANGE_TYPES

# NOTE: This command is implemented as a simple wrapper around the generic
# EOxServer command.

class Command(eoxs_rangetype_load.Command):

    option_list = BaseCommand.option_list + (
        make_option(
            '-i', '--input', dest='filename', action='store', type='string',
            default=RANGE_TYPES, help=(
                "Optional. Read input from a given file or standard input "
                "when dash (-) character is used. By default, the package's "
                "are used."
            )
        ),
    )

    help = (
        "Load range-types stored in JSON file or from the default package's \n"
        "range type definitions stores in: \n\t%s" % RANGE_TYPES
    )
