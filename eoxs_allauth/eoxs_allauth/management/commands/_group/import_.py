#-------------------------------------------------------------------------------
#
# Group management - import groups from a JSON file.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2026 EOX IT Services GmbH
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
from traceback import print_exc
from django.db import transaction
from django.contrib.auth.models import Group
from .._common import Subcommand


class ImportGroupSubcommand(Subcommand):
    name = "import"
    help = "Import groups from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input JSON file-name. "
                "By default, the groups' definitions are read from the "
                "standard input."
            )
        )

    def handle(self, **kwargs):
        filename = kwargs['filename']

        with sys.stdin if filename == "-" else open(filename, "rb") as file_:
            self.save_groups(json.load(file_), **kwargs)


    def save_groups(self, data, **kwargs):
        failed_count = 0
        created_count = 0
        updated_count = 0
        for item in data:
            name = item.get("name")
            try:
                is_updated = save_group(item)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error("Failed to create or update group %s! %s", name, error)
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info(
                    "group %s updated" if is_updated else "group %s created",
                    name, log=True
                )

        if created_count:
            self.info(
                "%d of %d group%s created", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d group%s updated", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d group%s failed to be imported", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )
        sys.exit(failed_count)


@transaction.atomic
def save_group(data):
    is_updated, user = get_group(data["name"])
    user.save()

    return is_updated


def get_group(name):
    try:
        return True, Group.objects.get(name=name)
    except Group.DoesNotExist:
        return False, Group(name=name)
