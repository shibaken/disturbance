# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-10-05 03:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0182_remove_approval_apiary_renewal_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='renewaldocument',
            name='for_expiry_date',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
