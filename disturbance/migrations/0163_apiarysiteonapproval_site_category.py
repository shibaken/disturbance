# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-17 04:10
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0162_auto_20200917_1209'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='site_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='disturbance.SiteCategory'),
        ),
    ]