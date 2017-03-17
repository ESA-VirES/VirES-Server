# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vires', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='started',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='status',
            field=models.CharField(default=b'U', max_length=1, choices=[(b'A', b'ACCEPTED'), (b'R', b'STARTED'), (b'S', b'SUCCEEDED'), (b'T', b'ABORTED'), (b'F', b'FAILED'), (b'U', b'UNDEFINED')]),
        ),
        migrations.AddField(
            model_name='job',
            name='stopped',
            field=models.DateTimeField(null=True),
        ),
    ]
