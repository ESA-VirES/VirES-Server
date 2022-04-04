#-------------------------------------------------------------------------------
#
#  EOIAM provider - extra utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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

from django.db import transaction
from django.contrib.auth.models import Group


def update_user_groups_from_permissions(user, permissions,
                                        required_group_permissions, logger):
    """ Update user groups from the received permissions. """
    groups_removed, groups_added = [], []

    for group, required_permissions_list in required_group_permissions.items():
        if _is_permitted(permissions, required_permissions_list):
            groups_added.append(group)
        else:
            groups_removed.append(group)

    _log_changes(logger, user, *update_groups(user, groups_added, groups_removed))


def _log_changes(logger, user, groups_added, groups_removed):
    for group in groups_added:
        logger.info("user %s added to %s", user.username, group)
    for group in groups_removed:
        logger.info("user %s removed from %s", user.username, group)


def _is_permitted(possessed_permissions, required_permissions_list):
    for required_permissions in required_permissions_list:
        if not required_permissions - possessed_permissions:
            return True
    return False


@transaction.atomic
def update_groups(user, group_names_added, group_names_removed):

    groups_removed = user.groups.filter(name__in=group_names_removed)
    group_names_removed = list(groups_removed.value_list("name", flat=True))
    user.groups.remove(*groups_removed)

    groups_added = (
        Group.objects
        .fliter(name__in=group_names_added)
        .exclude(id__in=user.groups.values("id"))
    )
    group_names_added = list(groups_added.value_list("name", flat=True))
    user.groups.add(*groups_added)

    return group_names_added, group_names_removed
