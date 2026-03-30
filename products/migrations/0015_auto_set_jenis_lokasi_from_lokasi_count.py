from django.db import migrations


def sync_jenis_lokasi_from_lokasi_count(apps, schema_editor):
    DocumentationRequest = apps.get_model("products", "DocumentationRequest")
    db_alias = schema_editor.connection.alias
    lokasi_through = DocumentationRequest.lokasi.through

    lokasi_count_map = {}
    for row in lokasi_through.objects.using(db_alias).all():
        lokasi_count_map[row.documentationrequest_id] = lokasi_count_map.get(row.documentationrequest_id, 0) + 1

    for documentation_request in DocumentationRequest.objects.using(db_alias).all().iterator():
        jenis_lokasi = "MULTI" if lokasi_count_map.get(documentation_request.id, 0) > 1 else "SINGLE"
        DocumentationRequest.objects.using(db_alias).filter(pk=documentation_request.pk).update(
            jenis_lokasi=jenis_lokasi
        )


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0014_documentationrequestlokasiassignment_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_jenis_lokasi_from_lokasi_count, migrations.RunPython.noop),
    ]
