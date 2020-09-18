# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-17 04:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0161_merge_20200917_1209'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='site_category_draft',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intermediate_draft', to='disturbance.SiteCategory'),
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='site_category_processed',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intermediate_processed', to='disturbance.SiteCategory'),
        ),
    ]