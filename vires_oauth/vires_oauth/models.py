#-------------------------------------------------------------------------------
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring

from django.db.models import (
    CASCADE, Model, OneToOneField, CharField,
)
from django.contrib.auth.models import User, Group, Permission
from django_countries.fields import CountryField
from .settings import PERMISSIONS, PACKAGE_NAME


class Permissions(Model):
    """ Dummy model holding app specific permissions. """
    class Meta:
        managed = False
        permissions = [item for item in PERMISSIONS.items()]


def get_permissions():
    """ Get a dictionary mapping permission codes to permissions model
    instances.
    """
    return {
        permission.codename: permission
        for permission in filter_permissions(Permission.objects)
    }


def filter_permissions(query_set):
    return query_set.filter(
        content_type__app_label=PACKAGE_NAME,
        content_type__model='permissions',
        codename__in=list(PERMISSIONS),
    )


class UserProfile(Model):
    user = OneToOneField(User, on_delete=CASCADE)
    title = CharField(max_length=100, blank=True)
    institution = CharField(max_length=100, blank=True)
    country = CountryField(blank=True, blank_label='(select country)')
    study_area = CharField(max_length=200, blank=True)
    executive_summary = CharField(max_length=3000, blank=True)

    def __str__(self):
        return "<UserProfile: %s>" % self.user


class GroupInfo(Model):
    """ Model holding human readable information about a group. """
    group = OneToOneField(Group, on_delete=CASCADE)
    title = CharField(max_length=200, null=True, blank=True)
    description = CharField(max_length=3000, null=True, blank=True)

    def __str__(self):
        return "<GroupInfo: %s>" % self.group
