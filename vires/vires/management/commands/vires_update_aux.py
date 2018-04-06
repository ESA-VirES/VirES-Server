#-------------------------------------------------------------------------------
# $Id$
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

import sys
from os import rename, remove
from os.path import exists
from contextlib import closing
from urllib2 import urlopen
from optparse import make_option

from django.conf import settings
from django.core.management.base import CommandError, BaseCommand
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.aux import update_kp, update_dst

# URL time-out in seconds
URL_TIMEOUT = 25

def update(source, destination, updater, label, tmp_extension=None):
    """ Update index from the given source. """
    print "Updating %s from %s" % (
        label, source if source != '-' else '<standard input>'
    )

    is_url = (
        source.startswith("https://") or
        source.startswith("http://") or
        source.startswith("ftp://")
    )

    destination_tmp = destination + (tmp_extension or ".tmp")
    if exists(destination_tmp):
        remove(destination_tmp)

    try:
        if is_url:
            with closing(urlopen(source, timeout=URL_TIMEOUT)) as fin:
                updater(fin, destination_tmp)
        elif source == '-':
            updater(sys.stdin, destination_tmp)
        else:
            with open(source) as fin:
                updater(fin, destination_tmp)
        rename(destination_tmp, destination)
    except Exception:
        if exists(destination_tmp):
            remove(destination_tmp)
        raise


class Command(CommandOutputMixIn, BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            "--dst-url", "--dst-filename", "--dst", dest="dst_filename",
            action="store", default=None,
            help="Dst index source (-, file-name, or URL)."
        ),
        make_option(
            "--kp-url", "--kp-filename", "--kp", dest="kp_filename",
            action="store", default=None,
            help="Kp index source (-, file-name, or URL)."
        ),
    )

    #@nested_commit_on_success # There is no Django DB modification.
    def handle(self, *args, **kwargs):
        if kwargs["dst_filename"] is not None:
            update(
                kwargs["dst_filename"],
                settings.VIRES_AUX_DB_DST,
                update_dst, 'Dst-index'
            )
        if kwargs["kp_filename"] is not None:
            update(
                kwargs["kp_filename"],
                settings.VIRES_AUX_DB_KP,
                update_kp, 'Kp-index'
            )
