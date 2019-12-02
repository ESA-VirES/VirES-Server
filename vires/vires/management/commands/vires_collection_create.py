#-------------------------------------------------------------------------------
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
# pylint: disable=missing-docstring

from django.core.management.base import BaseCommand, CommandError
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from eoxserver.resources.coverages.models import RangeType
from vires.models import ProductCollection


class Command(CommandOutputMixIn, BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("identifier", help="Collection identifier.")
        parser.add_argument("range_type_name", help="Range type name.")

    @nested_commit_on_success
    def handle(self, *args, **kwargs):
        identifier = kwargs["identifier"]
        range_type_name = kwargs["range_type_name"]

        try:
            range_type = RangeType.objects.get(name=range_type_name)
        except RangeType.DoesNotExist:
            raise CommandError("Invalid range-type '%s'!" % range_type_name)

        collection = ProductCollection()
        collection.identifier = identifier
        collection.range_type = range_type

        collection.srid = 4326
        collection.min_x = -180
        collection.min_y = -90
        collection.max_x = 180
        collection.max_y = 90
        collection.size_x = 0
        collection.size_y = 1

        collection.full_clean()
        collection.save()
