# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2019-01-14 13:00
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0002_auto_20190111_1536'),
    ]

    operations = [
        migrations.AddField(
            model_name='integrationtestconfig',
            name='api_endpoint',
            field=models.URLField(default='http://localhost:8000/', help_text='URL completa de la API de series a usar como referenciaen los mail de error'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='integrationtestconfig',
            name='recipients',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Destinatarios'),
        ),
    ]
