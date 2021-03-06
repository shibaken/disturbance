# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-05-13 06:19
from __future__ import unicode_literals

import disturbance.components.compliances.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0040_auto_20200513_1344'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apiarysitefeeremainder',
            name='number_of_sites_left',
        ),
        migrations.AddField(
            model_name='apiarysitefeeremainder',
            name='date_used',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='compliancedocument',
            name='_file',
            field=models.FileField(max_length=500, upload_to=disturbance.components.compliances.models.update_proposal_complaince_filename),
        ),
    ]
