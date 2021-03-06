# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-05-13 01:27
from __future__ import unicode_literals

import disturbance.components.compliances.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0034_auto_20200512_1550'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiarySiteFeeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.AlterField(
            model_name='compliancedocument',
            name='_file',
            field=models.FileField(max_length=500, upload_to=disturbance.components.compliances.models.update_proposal_complaince_filename),
        ),
        migrations.AddField(
            model_name='apiarysitefee',
            name='apiary_site_fee_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='disturbance.ApiarySiteFeeType'),
        ),
    ]
