# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vires', '0004_clientstate_customdataset_custommodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='customdataset',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='custommodel',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
    ]
