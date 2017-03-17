# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('coverages', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='ForwardModel',
            fields=[
                ('coverage_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='coverages.Coverage')),
            ],
            options={
                'abstract': False,
            },
            bases=('coverages.coverage',),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('coverage_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='coverages.Coverage')),
                ('ground_path', django.contrib.gis.db.models.fields.MultiLineStringField(srid=4326, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('coverages.coverage',),
        ),
        migrations.CreateModel(
            name='ProductCollection',
            fields=[
                ('collection_ptr', models.OneToOneField(parent_link=True, auto_created=True, to='coverages.Collection')),
                ('product_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='vires.Product')),
            ],
            options={
                'verbose_name': 'Product Collection',
                'verbose_name_plural': 'Product Collections',
            },
            bases=('vires.product', 'coverages.collection'),
        ),
    ]
