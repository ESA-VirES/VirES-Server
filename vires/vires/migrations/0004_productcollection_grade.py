# Generated by Django 2.2.28 on 2023-09-27 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vires', '0003_cached_magnetic_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcollection',
            name='grade',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
