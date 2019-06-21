#-------------------------------------------------------------------------------
#
# DJango forms
#
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
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

import re
from logging import getLogger
from django.forms import Form, CharField, Textarea
from django_countries import countries
from django_countries.fields import LazyTypedChoiceField
from django_countries.widgets import CountrySelectWidget
from .models import UserProfile

# FIXME: Is this still relevant? If not remove it!
# When account is created via social, fire django-allauth signal to populate
# Django User record.
#from django.dispatch import receiver
#from django.contrib.auth.models import User
#from allauth.account.signals import user_signed_up


# Regular expression matching invalid user-name characters.
RE_USER_NAME_INVALID_CHARACTERS = re.compile('[^a-zA-Z0-9_.]+')


class UserProfileForm(Form):
    title = CharField(max_length=100, required=False)
    first_name = CharField(max_length=30, required=False)
    last_name = CharField(max_length=30, required=False)
    institution = CharField(max_length=100, required=False)
    country = LazyTypedChoiceField(
        choices=[('', '(select country)')] + list(countries),
        required=False,
        widget=CountrySelectWidget(),
    )
    study_area = CharField(max_length=200, required=False)
    executive_summary = CharField(
        max_length=3000,
        widget=Textarea(attrs={
            'placeholder': 'Fill in a brief description the intend data usage.',
            'rows': 4
        }),
        required=False,
    )

    def save_profile(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        user_profile = user.userprofile
        user_profile.title = self.cleaned_data['title']
        user_profile.institution = self.cleaned_data['institution']
        user_profile.country = self.cleaned_data['country']
        user_profile.study_area = self.cleaned_data['study_area']
        user_profile.executive_summary = self.cleaned_data['executive_summary']
        user_profile.save()

    @staticmethod
    def load_profile(user):
        user_profile = user.userprofile
        return {
            'title': user_profile.title,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'institution': user_profile.institution,
            'country': user_profile.country,
            'study_area': user_profile.study_area,
            'executive_summary': user_profile.executive_summary,
        }

    def __init__(self, user, *args, **kwargs):
        initial = self.load_profile(user)
        initial.update(kwargs.get('initial') or {})
        kwargs['initial'] = initial
        super(UserProfileForm, self).__init__(*args, **kwargs)


class SignupForm(Form):
    title = CharField(max_length=100, required=False)
    first_name = CharField(max_length=30, required=False)
    last_name = CharField(max_length=30, required=False)
    institution = CharField(max_length=100, required=False)
    country = LazyTypedChoiceField(
        choices=[('', '(select country)')] + list(countries),
        required=False,
        widget=CountrySelectWidget(),
    )
    study_area = CharField(max_length=200, required=False)
    executive_summary = CharField(
        max_length=3000,
        widget=Textarea(attrs={
            'placeholder': 'Fill in a brief description the intend data usage.',
            'rows': 4
        }),
        required=False,
    )

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        user_profile = UserProfile(
            user=user,
            title=self.cleaned_data['title'],
            institution=self.cleaned_data['institution'],
            country=self.cleaned_data['country'],
            study_area=self.cleaned_data['study_area'],
            executive_summary=self.cleaned_data['executive_summary'],
        )
        user_profile.full_clean()
        user_profile.save()

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        if hasattr(self, 'sociallogin'):
            provider = self.sociallogin.account.provider
            extra_data = self.sociallogin.account.extra_data
            getLogger(__name__).debug("%s: %s", provider, extra_data)
            if provider == 'linkedin_oauth2':
                initial = self.extract_linkedin(extra_data)
            elif provider == 'facebook':
                initial = self.extract_facebook(extra_data)
            elif provider == 'google':
                initial = self.extract_google(extra_data)
            elif provider == 'twitter':
                initial = self.extract_twitter(extra_data)
            else:
                initial = {}
            self.initial.update(initial)

    @classmethod
    def email_to_username(cls, email):
        """ Extract user-name from an e-mail address. """
        return RE_USER_NAME_INVALID_CHARACTERS.sub('', email.partition("@")[0])

    @classmethod
    def extract_linkedin(cls, extra_data):
        """ Extract user info form the LinkedIn social login. """
        data = {}
        if 'location' in extra_data:
            data['country'] = extra_data['location']['country']['code'].upper()
        if 'emailAddress' in extra_data:
            data['username'] = cls.email_to_username(extra_data['emailAddress'])
        if 'positions' in extra_data and 'values' in extra_data['positions']:
            for position in extra_data['positions']['values']:
                if 'isCurrent' in position and position['isCurrent']:
                    if 'company' in position:
                        data['institution'] = position['company']['name']
                    if 'title' in position:
                        data['title'] = position['title']
                    if 'summary' in position:
                        data['study_area'] = position['summary']
                    break
        return data

    @classmethod
    def extract_google(cls, extra_data):
        """ Extract user info form the Google social login. """
        data = {}
        if 'email' in extra_data:
            data['username'] = cls.email_to_username(extra_data['email'])
        return data

    @classmethod
    def extract_facebook(cls, extra_data):
        """ Extract user info form the LinkedIn social login. """
        data = {}
        if 'email' in extra_data:
            data['username'] = cls.email_to_username(extra_data['email'])
        return data

    @classmethod
    def extract_twitter(cls, extra_data):
        """ Extract user info form the Twitter social login. """
        return {}
