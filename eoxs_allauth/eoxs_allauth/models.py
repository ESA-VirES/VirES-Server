#-------------------------------------------------------------------------------
#
# Project: EOxServer - django-allauth integration.
# Authors: Daniel Santillan <daniel.santillan@eox.at>
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

import os
import base64

from django.db.models import (
    Model, OneToOneField, ForeignKey, CharField, DateTimeField,
    BooleanField,
)
from django.contrib.auth.models import User
from django_countries.fields import CountryField


class UserProfile(Model):
    user = OneToOneField(User)
    title = CharField(max_length=100, blank=True)
    institution = CharField(max_length=100, blank=True)
    country = CountryField(blank=True, blank_label='(select country)')
    study_area = CharField(max_length=200, blank=True)
    # TODO: Change executive_summary type to TextField.
    executive_summary = CharField(max_length=3000, blank=True)

    def __str__(self):
        return "<UserProfile: %s>" % self.user


def get_random_token(lenght):
    return base64.urlsafe_b64encode(os.urandom(lenght))

def get_default_identifier():
    return get_random_token(12)

def get_default_token():
    return get_random_token(24)


class AuthenticationToken(Model):
    owner = ForeignKey(User, related_name='tokens', null=False, blank=False)
    token = CharField(
        max_length=32, blank=True, null=True,
        default=get_default_token, unique=True
    )
    identifier = CharField(
        max_length=16, blank=True, null=True,
        default=get_default_identifier, unique=True,
    )
    is_new = BooleanField(default=False, null=False)
    created = DateTimeField(auto_now_add=True)
    expires = DateTimeField(null=True, default=None)
    purpose = CharField(max_length=128, blank=True, null=True)
