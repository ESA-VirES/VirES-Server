#-------------------------------------------------------------------------------
#
# Export user permissions in JSON format.
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
# pylint: disable=missing-docstring, too-few-public-methods

import sys
import json
from vires_oauth.models import Permission
from .._common import Subcommand, JSON_OPTS


class ExportPermissionSubcommand(Subcommand):
    name = "export"
    help = (
        "Export user permissions in JSON format. The exported permissions "
        "can be selected by names."
    )

    def add_arguments(self, parser):
        parser.add_argument("permissions", nargs="*", help="Selected permissions.")
        parser.add_argument(
            "-f", "--file-name", dest="filename", default="-", help=(
                "Optional output file-name. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        permissions = self.select_permissions(Permission.objects.all(), **kwargs)

        data = [serialize_permission(permission) for permission in permissions]

        filename = kwargs['filename']
        with sys.stdout if filename == "-" else open(filename, "w") as file_:
            json.dump(data, file_, **JSON_OPTS)

    def select_permissions(self, query, **kwargs):
        permissions = kwargs['permissions']
        if permissions:
            query = query.filter(name__in=permissions)
        return query


def serialize_permission(permission):
    return {
        "name": permission.name,
        "description": permission.description,
    }
