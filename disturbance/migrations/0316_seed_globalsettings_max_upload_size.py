from django.db import migrations


def seed_max_upload_size_setting(apps, schema_editor):
    GlobalSettings = apps.get_model('disturbance', 'GlobalSettings')
    GlobalSettings.objects.update_or_create(
        key='max_file_upload_size_mb',
        defaults={'value': '15'},
    )


def unseed_max_upload_size_setting(apps, schema_editor):
    GlobalSettings = apps.get_model('disturbance', 'GlobalSettings')
    GlobalSettings.objects.filter(key='max_file_upload_size_mb').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0315_alter_globalsettings_key'),
    ]

    operations = [
        migrations.RunPython(seed_max_upload_size_setting, unseed_max_upload_size_setting),
    ]
