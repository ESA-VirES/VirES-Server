# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vires', '0003_auto_20190429_0825'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientState',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('identifier', models.CharField(unique=True, max_length=64)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(null=True, blank=True)),
                ('state', models.TextField()),
                ('owner', models.ForeignKey(related_name='client_states', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CustomDataset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('identifier', models.CharField(unique=True, max_length=64)),
                ('filename', models.CharField(max_length=255)),
                ('location', models.CharField(max_length=4096)),
                ('size', models.BigIntegerField()),
                ('content_type', models.CharField(max_length=64)),
                ('checksum', models.CharField(max_length=64)),
                ('info', models.TextField(null=True, blank=True)),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CustomModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('identifier', models.CharField(unique=True, max_length=64)),
                ('filename', models.CharField(max_length=255)),
                ('location', models.CharField(max_length=4096)),
                ('size', models.BigIntegerField()),
                ('content_type', models.CharField(max_length=64)),
                ('checksum', models.CharField(max_length=64)),
                ('info', models.TextField(null=True, blank=True)),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
