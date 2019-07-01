#-------------------------------------------------------------------------------
#
# Dump user groups.
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
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from ...models import GroupInfo, filter_permissions
from ._common import CommandMixIn

JSON_OPTS = {'sort_keys': False, 'indent': 2, 'separators': (',', ': ')}


class Command(CommandMixIn, BaseCommand):
    help = (
        "Dump groups in JSON format. The groups can be selected by "
        "the provided group names."
    )

    def add_arguments(self, parser):
        parser.add_argument("groups", nargs="*", help="Selected groups.")
        parser.add_argument(
            "-f", "--file-name", dest="filename", default="-", help=(
                "Optional output file-name. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, groups, filename, **kwargs):
        # select user profile
        query = Group.objects.select_related('groupinfo')
        if not groups:
            query = query.all()
        else:
            query = query.filter(name__in=groups)
        data = [
            extract_group(group) for group in query
        ]

        with sys.stdout if filename == "-" else open(filename, "w") as file_:
            json.dump(data, file_, **JSON_OPTS)


def extract_group(group):
    """ Extract group data from a model. """

    data = {
        "name": group.name,
        "permissions": [
            permission.codename for permission
            in filter_permissions(group.permissions)
        ],
    }
    try:
        group_info = group.groupinfo
        data.update({
            "title": group_info.title,
            "description": group_info.description,
        })
    except GroupInfo.DoesNotExist:
        pass

    return {
        key: value for key, value in data.items() if value not in (None, "")
    }
