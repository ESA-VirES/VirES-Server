

from django.db import models
from django.contrib.auth.models import User
from django_countries.fields import CountryField


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    title = models.CharField(max_length=100, blank=True)
    institution = models.CharField(max_length=100, blank=True)
    country = CountryField(blank=True, blank_label='(select country)')
    study_area = models.CharField(max_length=200, blank=True)
    executive_summary = models.CharField(max_length=3000, blank=True)
