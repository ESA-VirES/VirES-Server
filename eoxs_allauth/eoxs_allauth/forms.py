
from itertools import chain
from django import forms
from django.contrib.auth.models import User

from django.forms import ModelForm
from eoxs_allauth.models import UserProfile

from django_countries.fields import LazyTypedChoiceField
from django_countries.fields import CountryField
from django_countries import countries
from django_countries.widgets import CountrySelectWidget


# When account is created via social, fire django-allauth signal to populate Django User record.
from allauth.account.signals import user_signed_up
from django.dispatch import receiver


my_countries = list(chain((('', '-------'),), countries))

class ProfileForm(ModelForm):
     class Meta:
         model = UserProfile
         fields = ['title', 'institution', 'country', 'study_area', 'executive_summary']
         widgets = {'country': CountrySelectWidget()}


class ESASignupForm(forms.Form):

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    title = forms.CharField(max_length=100, required=False)
    institution = forms.CharField(max_length=100, required=False)

    country = LazyTypedChoiceField(
        choices=my_countries,
        required=False,
        widget=CountrySelectWidget())

    study_area = forms.CharField(max_length=200, required=False)
    executive_summary = forms.CharField(max_length=3000, required=False)


    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        user_profile = UserProfile(
            user = user,
            title = self.cleaned_data['title'],
            institution = self.cleaned_data['institution'],
            country = self.cleaned_data['country'],
            study_area = self.cleaned_data['study_area'],
            executive_summary = self.cleaned_data['executive_summary'],
        )

        user_profile.full_clean()
        user_profile.save()
    

    def __init__(self, *args, **kwargs):
        super(ESASignupForm, self).__init__(*args, **kwargs)
        if hasattr(self, 'sociallogin'):

            ed = self.sociallogin.account.extra_data

            if self.sociallogin.account.provider == 'linkedin_oauth2':
                if 'location' in ed:
                    self.initial['country'] = ed['location']['country']['code'].upper()
                if 'emailAddress' in ed:
                    self.initial['username'] = ed['emailAddress'].split('@')[0]
                if 'positions' in ed:
                    for i in range(0, len(ed['positions'])-1):
                        if ed['positions']['values'][i]['isCurrent']:
                            self.initial['institution'] = ed['positions']['values'][i]['company']['name']
                            self.initial['title'] = ed['positions']['values'][i]['title']
                            self.initial['study_area'] = ed['positions']['values'][i]['summary']
            
            # TODO: Need to activate and review app by facebook in order to get 
            # more information from user
            #if self.sociallogin.account.provider == 'facebook':
            #if self.sociallogin.account.provider == 'google':
            #    self.initial['institution'] = ed
            #if self.sociallogin.account.provider == 'twitter':

                            

                