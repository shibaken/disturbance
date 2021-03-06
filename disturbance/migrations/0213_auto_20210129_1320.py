# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-29 05:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0212_proposal_weekly_reminder_sent_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalrequirement',
            name='copied_for_renewal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='proposalrequirement',
            name='require_due_date',
            field=models.BooleanField(default=False),
        ),
    ]
