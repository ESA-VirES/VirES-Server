# Generated by Django 2.2.10 on 2020-05-16 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eoxs_allauth', '0003_token_sha256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authenticationtoken',
            name='token_sha256',
            field=models.BinaryField(max_length=32, unique=True),
        ),
        migrations.RemoveField(
            model_name='authenticationtoken',
            name='is_new',
        ),
        migrations.RemoveField(
            model_name='authenticationtoken',
            name='token',
        ),
    ]
