# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-05-25 07:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0045_merge_20200515_1350'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiaryApplicantChecklistAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.NullBooleanField()),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='apiary_applicant_checklist', to='disturbance.Proposal')),
            ],
            options={
                'verbose_name': 'CheckList answer',
                'verbose_name_plural': 'CheckList answers',
            },
        ),
        migrations.RenameModel(
            old_name='ApiaryChecklistQuestion',
            new_name='ApiaryApplicantChecklistQuestion',
        ),
        migrations.AddField(
            model_name='apiaryapplicantchecklistanswer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='disturbance.ApiaryApplicantChecklistQuestion'),
        ),
    ]
