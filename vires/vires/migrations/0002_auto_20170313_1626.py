# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('vires', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(max_length=256)),
                ('process_id', models.CharField(max_length=256)),
                ('response_url', models.CharField(max_length=512)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(related_name='jobs', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('started', models.DateTimeField(null=True)),
                ('status', models.CharField(default=b'U', max_length=1, choices=[(b'A', b'ACCEPTED'), (b'R', b'STARTED'), (b'S', b'SUCCEEDED'), (b'T', b'ABORTED'), (b'F', b'FAILED'), (b'U', b'UNDEFINED')])),
                ('stopped', models.DateTimeField(null=True)),
            ],
            options={
                'verbose_name': 'WPS Job',
                'verbose_name_plural': 'WPS Jobs',
            },
        ),
    ]
