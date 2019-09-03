#-------------------------------------------------------------------------------
#
# VirES OAuth2  signal handlers
#
# Authors: Martin Paces <martin.paces@eox.at>
#
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
# pylint: disable=missing-docstring, invalid-name

from logging import getLogger
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.models import Group
from allauth.account.signals import user_signed_up


@receiver(user_signed_up)
def set_default_group(sender, request, user, **kwargs):
    """ Set default groups for newly signed-up users. """
    logger = getLogger(__name__)
    default_group = getattr(settings, "VIRES_OAUTH_DEFAULT_GROUP", None)
    if not default_group:
        return
    try:
        group = Group.objects.get(name=default_group)
    except Group.DoesNotExist:
        logger.warning("Default group %s does not exist!", default_group)
        return
    user.groups.add(group)
    logger.debug("User %s added to group %s.", user.username, group.name)
