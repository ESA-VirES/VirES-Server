#-------------------------------------------------------------------------------
#
# Import user groups from a JSON file
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
from traceback import print_exc
from contextlib import suppress
from django.db import transaction
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from ...models import GroupInfo, Permission
from ...data import DEFAULT_GROUPS
from ._common import ConsoleOutput


class Command(ConsoleOutput, BaseCommand):
    help = "Import groups from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional input file-name. "
                "By default it is read from the standard input."
            )
        )
        parser.add_argument(
            "-d", "--default", dest="load_defaults", action="store_true",
            default=False, help="Re-load default set of groups."
        )

    def handle(self, filename, load_defaults, **kwargs):

        if load_defaults:
            filename = DEFAULT_GROUPS

        with sys.stdin.buffer if filename == "-" else open(filename, "rb") as file_:
            data = json.load(file_)

        permissions = get_permissions()

        failed_count = 0
        created_count = 0
        updated_count = 0
        for item in data:
            name = item['name']
            try:
                is_updated = save_group(item, permissions)
            except Exception as error:
                failed_count += 1
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error("Failed to create or update a group! %s", error)
            else:
                updated_count += is_updated
                created_count += not is_updated
                self.info((
                    "Existing user group %s updated." if is_updated else
                    "New user group %s created."
                ), name)

        if created_count:
            self.info(
                "%d of %d user group%s updated.", created_count, len(data),
                "s" if created_count > 1 else ""
            )

        if updated_count:
            self.info(
                "%d of %d user group%s updated.", updated_count, len(data),
                "s" if updated_count > 1 else ""
            )

        if failed_count:
            self.info(
                "%d of %d user group%s failed ", failed_count, len(data),
                "s" if failed_count > 1 else ""
            )

@transaction.atomic
def save_group(item, permissions):
    name = item['name']
    try:
        group = Group.objects.get(name=name)
        is_updated = True
    except Group.DoesNotExist:
        group = Group(name=name)
        is_updated = False

    group.save()

    group.permissions.clear()
    for permission_name in item.get('permissions') or []:
        with suppress(KeyError):
            group.oauth_user_permissions.add(permissions[permission_name])

    if 'title' in item:
        try:
            group_info = group.groupinfo
        except GroupInfo.DoesNotExist:
            group_info = GroupInfo()
            group_info.group = group

        group_info.title = item['title']
        group_info.save()

    return is_updated

def get_permissions():
    return {
        permission.name: permission
        for permission in Permission.objects.all()
    }
