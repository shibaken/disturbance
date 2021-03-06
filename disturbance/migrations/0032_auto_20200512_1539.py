# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-05-12 07:39
from __future__ import unicode_literals

import disturbance.components.compliances.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0031_auto_20200512_1155'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiarySiteFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fee_type', models.CharField(choices=[('new_application', 'New Application'), ('amendment', 'Amendment'), ('renewal', 'Renewal'), ('transfer', 'Transfer')], default='new_application', max_length=40)),
                ('amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=8)),
                ('date_of_enforcement', models.DateField(blank=True, null=True)),
                ('site_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='site_fees', to='disturbance.SiteCategory')),
            ],
            options={
                'ordering': ('date_of_enforcement',),
            },
        ),
        migrations.AlterField(
            model_name='compliancedocument',
            name='_file',
            field=models.FileField(max_length=500, upload_to=disturbance.components.compliances.models.update_proposal_complaince_filename),
        ),
        migrations.AlterUniqueTogether(
            name='apiarysitefee',
            unique_together=set([('fee_type', 'site_category')]),
        ),
    ]
