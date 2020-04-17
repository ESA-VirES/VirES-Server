#-------------------------------------------------------------------------------
#
# Export product types in JSON format.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
from vires.models import ProductType
from .._common import Subcommand, JSON_OPTS, datetime_to_string


class ExportProductTypeSubcommand(Subcommand):
    name = "export"
    help = "Export product type definitions as a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "-f", "--file-name", dest="file", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        query = ProductType.objects.order_by('identifier')

        identifiers = kwargs['identifier']
        if identifiers:
            query = query.filter(identifier__in=identifiers)

        data = [serialize_type(ptype) for ptype in query.all()]

        filename = kwargs["file"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def serialize_type(object_):
    return {
        "name": object_.identifier,
        "created": datetime_to_string(object_.created),
        "updated": datetime_to_string(object_.updated),
        **object_.definition,
    }
