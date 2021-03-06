# Generated by Django 2.2.15 on 2020-09-18 16:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vires', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'DROP VIEW IF EXISTS vires_productlocation;'
                'CREATE OR REPLACE VIEW vires_productlocation AS '
                '  SELECT '
                '    ROW_NUMBER() OVER () as id, '
                '    product_id, '
                '    location '
                '  FROM ( '
                '    SELECT DISTINCT '
                '      vires_product.id as product_id, '
                '      dataset_item.value->>\'location\' AS location '
                '    FROM vires_product, JSONB_EACH(datasets) AS dataset_item '
                '  ) AS locations ;'
            ),
            reverse_sql=(
                'DROP VIEW IF EXISTS vires_productlocation;'
            )
        ),
        migrations.CreateModel(
            name='ProductLocation',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('location', models.CharField(max_length=1024)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='vires.Product')),
            ],
            options={
                'db_table': 'vires_productlocation',
                'managed': False,
            },
        ),
    ]
