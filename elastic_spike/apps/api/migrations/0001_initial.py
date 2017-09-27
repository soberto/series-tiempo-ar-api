# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-09-19 14:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Catalog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metadata', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metadata', models.TextField()),
                ('catalog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Catalog')),
            ],
        ),
        migrations.CreateModel(
            name='Distribution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metadata', models.TextField()),
                ('download_url', models.URLField()),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Dataset')),
            ],
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metadata', models.TextField()),
                ('distribution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Distribution')),
            ],
        ),
    ]