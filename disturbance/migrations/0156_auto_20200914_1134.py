# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-14 03:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0155_auto_20200911_0941'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apiarysite',
            name='available',
        ),
        migrations.RemoveField(
            model_name='apiarysite',
            name='district',
        ),
        migrations.RemoveField(
            model_name='apiarysite',
            name='pending_payment',
        ),
        migrations.RemoveField(
            model_name='apiarysite',
            name='region',
        ),
        migrations.RemoveField(
            model_name='apiarysite',
            name='status',
        ),
        migrations.RemoveField(
            model_name='apiarysite',
            name='workflow_selected_status',
        ),
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='link_connected',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='site_available',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='site_status',
            field=models.CharField(choices=[('current', 'Current'), ('not_to_be_reissued', 'Not to be reissued'), ('suspended', 'Suspended')], default='current', max_length=20),
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='link_connected',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='site_status',
            field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending'), ('pending_payment', 'Pending payment'), ('approved', 'Approved'), ('denied', 'Denied')], default='draft', max_length=20),
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='workflow_selected_status',
            field=models.BooleanField(default=False),
        ),
    ]
