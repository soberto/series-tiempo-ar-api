# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-03-21 12:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0008_auto_20180320_1215'),
    ]

    operations = [
        migrations.AlterField(
            model_name='indicator',
            name='type',
            field=models.CharField(choices=[('catalogos_nuevos_cant', 'Cat\xe1logos nuevos'), ('catalogos_cant', 'Cat\xe1logos totales'), ('catalogos_actualizados_cant', 'Cat\xe1logos actualizados'), ('catalogos_no_actualizados_cant', 'Cat\xe1logos no actualizados'), ('datasets_nuevos_cant', 'Datasets nuevos'), ('datasets_cant', 'Datasets totales'), ('datasets_actualizados_cant', 'Datasets actualizados'), ('datasets_no_actualizados_cant', 'Datasets no actualizados'), ('dataset_indexables_cant', 'Datasets indexables'), ('datasets_no_indexables_cant', 'Datasets no indexables'), ('datasets_error_cant', 'Datasets con errores'), ('distribuciones_nuevas_cant', 'Distribuciones nuevas'), ('distribuciones_cant', 'Distribuciones totales'), ('distribuciones_actualizadas_cant', 'Distribuciones actualizadas'), ('distribuciones_no_actualizadas_cant', 'Distribuciones no actualizadas'), ('distribuciones_indexables_cant', 'Distribuciones indexables'), ('distribuciones_no_indexables_cant', 'Distribuciones no indexables'), ('distribuciones_error_cant', 'Distribuciones con error'), ('series_nuevas_cant', 'Series nuevas'), ('field_cant', 'Series totales'), ('series_actualizadas_cant', 'Series actualizadas'), ('series_no_actualizadas_cant', 'Series no actualizadas'), ('series_indexables_cant', 'Series indexables'), ('series_no_indexables_cant', 'Series no indexables'), ('series_error_cant', 'Series con error')], max_length=100),
        ),
    ]
