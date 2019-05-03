# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webclient', '0001_initial'),
        ('coverages', '0001_initial'),
        ('backends', '0001_initial'),
        ('services', '0001_initial'),
        ('vires', '0002_auto_20170313_1626'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forwardmodel',
            name='coverage_ptr',
        ),
        migrations.RemoveField(
            model_name='product',
            name='ground_path',
        ),
        migrations.DeleteModel(
            name='ForwardModel',
        ),
    ]
