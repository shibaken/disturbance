from django.db import migrations


def seed_max_upload_size_internal_setting(apps, schema_editor):
    GlobalSettings = apps.get_model('disturbance', 'GlobalSettings')
    GlobalSettings.objects.update_or_create(
        key='max_file_upload_size_mb_internal',
        defaults={'value': '50'},
    )


def unseed_max_upload_size_internal_setting(apps, schema_editor):
    GlobalSettings = apps.get_model('disturbance', 'GlobalSettings')
    GlobalSettings.objects.filter(key='max_file_upload_size_mb_internal').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0317_alter_globalsettings_key'),
    ]

    operations = [
        migrations.RunPython(seed_max_upload_size_internal_setting, unseed_max_upload_size_internal_setting),
    ]
