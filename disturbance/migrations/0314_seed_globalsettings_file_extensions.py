from django.db import migrations


def seed_file_extension_settings(apps, schema_editor):
    GlobalSettings = apps.get_model('disturbance', 'GlobalSettings')
    GlobalSettings.objects.update_or_create(
        key='allowed_file_extensions',
        defaults={'value': 'pdf, png, jpg, jpeg, doc, docx, xls, xlsx, csv, txt, msg, eml'},
    )
    GlobalSettings.objects.update_or_create(
        key='allowed_gis_archive_extensions',
        defaults={'value': 'shp, shx, dbf, prj, sbn, sbx, cpg, qix, xml, geojson, json, gpkg'},
    )


def unseed_file_extension_settings(apps, schema_editor):
    GlobalSettings = apps.get_model('disturbance', 'GlobalSettings')
    GlobalSettings.objects.filter(
        key__in=['allowed_file_extensions', 'allowed_gis_archive_extensions'],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0313_alter_globalsettings_key'),
    ]

    operations = [
        migrations.RunPython(seed_file_extension_settings, unseed_file_extension_settings),
    ]
