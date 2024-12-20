# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-07-26 21:48
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0294_auto_20240715_0958'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='proposal',
            name='proposal_geom',
        ),
        migrations.AddField(
            model_name='proposal',
            name='shapefile_geom',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326, verbose_name='Source/Submitter gdf.exploded (multi) polygon geometry'),
        ),
    ]
