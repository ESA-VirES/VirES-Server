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

from logging import getLogger
from optparse import make_option

from django.conf import settings
from django.core.management.base import CommandError, BaseCommand
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.aux import update_kp, update_dst
from vires.cached_products import (
    update_cached_product, simple_cached_product_updater,
)

DEPRECATION_WARNING =(
    "The 'vires_update_aux' command is deprecated! "
    "Use 'vires_update_cached_file' instead."
)


class Command(CommandOutputMixIn, BaseCommand):
    help = DEPRECATION_WARNING
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

    def handle(self, *args, **kwargs):
        logger=getLogger(__name__)
        logger.warn(DEPRECATION_WARNING)

        def _update(source, destination, updater):
            update_cached_product(
                [source], destination, simple_cached_product_updater(updater),
                tmp_extension=".tmp.cdf", logger=logger
            )

        if kwargs["dst_filename"] is not None:
            _update(
                kwargs["dst_filename"], settings.VIRES_AUX_DB_DST, update_dst
            )

        if kwargs["kp_filename"] is not None:
            _update(
                kwargs["kp_filename"], settings.VIRES_AUX_DB_KP, update_kp
            )
