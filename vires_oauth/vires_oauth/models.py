#-------------------------------------------------------------------------------
#
# OAuth server models
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

import datetime
from django.db.models import (
    CASCADE, Model, ManyToManyField, OneToOneField, CharField, Subquery,
    BooleanField, DateTimeField,
)
from django.contrib.auth.models import User, Group
from django_countries.fields import CountryField
from .time_utils import now


class Challenge(Model):
    challenge = CharField(max_length=128, null=False, blank=False, unique=True)
    used = BooleanField(default=False, null=False, blank=False)
    expires = DateTimeField(null=True, blank=True)
    created = DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return not self.used and (self.expires is None or self.expires > now())


class Permission(Model):
    groups = ManyToManyField(
        Group,
        related_name='oauth_user_permissions',
        related_query_name='oauth_user_permission',
    )
    name = CharField(max_length=100, null=False, blank=False, unique=True)
    description = CharField(max_length=256, null=False, blank=False)

    @classmethod
    def get_user_permissions(cls, user):
        query = cls.objects.distinct().filter(
            groups__id__in=Subquery(user.groups.all().values('id'))
        ).values_list('name', 'description')
        return {name: description for name, description in query}


class UserProfile(Model):
    user = OneToOneField(User, on_delete=CASCADE)
    title = CharField(max_length=100, blank=True)
    institution = CharField(max_length=100, blank=True)
    country = CountryField(blank=True, blank_label='(select country)')
    study_area = CharField(max_length=200, blank=True)
    executive_summary = CharField(max_length=3000, blank=True)
    # The following filed contains the consented version of the Service Terms
    # and related documents.
    consented_service_terms_version = CharField(
        max_length=32, default="", blank=True
    )

    def __str__(self):
        return "<UserProfile: %s>" % self.user


class GroupInfo(Model):
    """ Model holding human readable information about a group. """
    group = OneToOneField(Group, on_delete=CASCADE)
    title = CharField(max_length=200, null=True, blank=True)
    description = CharField(max_length=3000, null=True, blank=True)

    def __str__(self):
        return "<GroupInfo: %s>" % self.group
