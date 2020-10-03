#-------------------------------------------------------------------------------
#
# Export user groups in JSON format.
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
from django.contrib.auth.models import Group
from vires_oauth.models import GroupInfo
from .._common import JSON_OPTS, Subcommand, strip_blanks


class ExportGroupSubcommand(Subcommand):
    name = "export"
    help = "Export user groups in JSON format."

    def add_arguments(self, parser):
        parser.add_argument("groups", nargs="*", help="Selected groups.")
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        groups = self.select_groups(
            Group.objects.select_related('groupinfo'), **kwargs
        )

        data = [serialize_group(group) for group in groups]

        filename = kwargs["filename"]
        with sys.stdout if filename == "-" else open(filename, "w") as file_:
            json.dump(data, file_, **JSON_OPTS)


    def select_groups(self, query, **kwargs):
        groups = kwargs['groups']
        if not groups:
            query = query.all()
        else:
            query = query.filter(name__in=groups)
        return query


@strip_blanks
def serialize_group(group):
    """ Extract group data from a model. """
    data = {
        "name": group.name,
        "permissions": [
            permission.name for permission in group.oauth_user_permissions.all()
        ],
    }
    try:
        data.update(serialize_group_info(group.groupinfo))
    except GroupInfo.DoesNotExist:
        pass
    return data


def serialize_group_info(group_info):
    """ Extract group info data from a model. """
    return {
        "title": group_info.title,
        "description": group_info.description,
    }
