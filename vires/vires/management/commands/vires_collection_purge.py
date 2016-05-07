#-------------------------------------------------------------------------------
#
# Products management - fast de-registration
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=fixme, import-error, no-self-use, broad-except
# pylint: disable=missing-docstring, too-many-locals, too-many-branches
# pylint: disable=redefined-variable-type

#from optparse import make_option
from django.core.management.base import CommandError, BaseCommand
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from eoxserver.resources.coverages.models import Collection


class Command(CommandOutputMixIn, BaseCommand):
    help = "De-register all products from the selected collections."
    args = "[<collection> [<collection> ...]]"
    option_list = BaseCommand.option_list

    @nested_commit_on_success
    def handle(self, *args, **kwargs):
        count = 0

        for collection_id in args:
            try:
                collection = Collection.objects.get(identifier=collection_id)
            except Collection.DoesNotExist:
                self.print_wrn(
                    "The collection '%s' does not exist!" % collection_id
                )
                continue

            for coverage in (
                item.cast() for item in collection.eo_objects.all()
                if item.iscoverage
            ):
                self.print_msg(
                    "De-registering dataset: '%s'" % coverage.identifier
                ) 
                coverage.delete()
                count += 1

        self.print_msg("%s dataset%s de-registered." % (
            "No" if count == 0 else "%d" % count, "s" if count > 1 else "" 
        ))
