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

from secrets import token_urlsafe
from hashlib import sha256
from django.db.models import (
    Model, OneToOneField, ForeignKey, BinaryField, CharField, DateTimeField,
    BooleanField, CASCADE,
)
from django.utils.timezone import now
from django.contrib.auth.models import User
from django_countries.fields import CountryField


class UserProfile(Model):
    user = OneToOneField(User, on_delete=CASCADE)
    title = CharField(max_length=100, blank=True)
    institution = CharField(max_length=100, blank=True)
    country = CountryField(blank=True, blank_label='(select country)')
    study_area = CharField(max_length=200, blank=True)
    # TODO: Change executive_summary type to TextField.
    executive_summary = CharField(max_length=3000, blank=True)

    def __str__(self):
        return "<UserProfile: %s>" % self.user


def get_default_identifier():
    return token_urlsafe(12)


def get_default_token():
    return token_urlsafe(24)


class AuthenticationToken(Model):

    owner = ForeignKey(
        User, related_name='tokens', null=False, blank=False, on_delete=CASCADE
    )
    token_sha256 = BinaryField(
        max_length=32, blank=False, null=False, unique=True,
    )
    identifier = CharField(
        max_length=16, blank=True, null=True,
        default=get_default_identifier, unique=True,
    )
    created = DateTimeField(auto_now_add=True)
    expires = DateTimeField(null=True, default=None)
    purpose = CharField(max_length=128, blank=True, null=True)

    @property
    def is_expired(self):
        """ True if model is expired. """
        return self.expires and self.expires <= now()

    def set_new_token(self):
        """ Create new token and set hash in the model. """
        token = get_default_token()
        self.token_sha256 = self.hash_token_sha256(token)
        return token

    @classmethod
    def find_object_by_token(cls, token):
        """ Find object for the given token or return None. """
        try:
            token_obj = (
                cls.objects.select_related('owner')
                .get(token_sha256=AuthenticationToken.hash_token_sha256(token))
            )
        except cls.DoesNotExist:
            return None
        if token_obj.is_expired:
            token_obj.delete()
            return None
        return token_obj

    @staticmethod
    def hash_token_sha256(token):
        """ Binary digest of the hashed token. """
        return sha256(token.encode('utf-8')).digest()
