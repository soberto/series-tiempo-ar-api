# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2019-02-08 18:09
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0006_auto_20190123_1530'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='metadataconfig',
            name='time',
        ),
    ]
