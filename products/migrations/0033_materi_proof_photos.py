from django.db import migrations, models


def move_parent_proofs_to_default_materi(apps, schema_editor):
    DocumentationRequest = apps.get_model("products", "DocumentationRequest")
    MaintenanceRequest = apps.get_model("products", "MaintenanceRequest")

    for doc_request in DocumentationRequest.objects.exclude(
        foto_bukti_kerja=""
    ).exclude(foto_bukti_kerja__isnull=True).iterator():
        materi = doc_request.materi_items.order_by("sort_order", "id").first()
        if materi and not materi.foto_bukti_kerja:
            materi.foto_bukti_kerja = doc_request.foto_bukti_kerja
            materi.save(update_fields=["foto_bukti_kerja"])

    for maint_request in MaintenanceRequest.objects.exclude(
        foto_bukti_kerja=""
    ).exclude(foto_bukti_kerja__isnull=True).iterator():
        materi = maint_request.materi_items.order_by("sort_order", "id").first()
        if materi and not materi.foto_bukti_kerja:
            materi.foto_bukti_kerja = maint_request.foto_bukti_kerja
            materi.save(update_fields=["foto_bukti_kerja"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0032_doc_maint_brand_materi_children"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentationrequestmateri",
            name="foto_bukti_kerja",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="doc_request_proofs/",
                verbose_name="Foto Bukti Kerja",
            ),
        ),
        migrations.AddField(
            model_name="maintenancerequestmateri",
            name="foto_bukti_kerja",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="maintenance_proofs/",
                verbose_name="Foto Bukti Kerja",
            ),
        ),
        migrations.RunPython(move_parent_proofs_to_default_materi, migrations.RunPython.noop),
    ]
