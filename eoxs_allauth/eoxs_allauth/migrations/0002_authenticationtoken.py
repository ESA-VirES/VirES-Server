# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import eoxs_allauth.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('eoxs_allauth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthenticationToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(default=eoxs_allauth.models.get_default_token, max_length=32, unique=True, null=True, blank=True)),
                ('identifier', models.CharField(default=eoxs_allauth.models.get_default_identifier, max_length=16, unique=True, null=True, blank=True)),
                ('is_new', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('expires', models.DateTimeField(default=None, null=True)),
                ('purpose', models.CharField(max_length=128, null=True, blank=True)),
                ('owner', models.ForeignKey(related_name='tokens', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
        ),
    ]
