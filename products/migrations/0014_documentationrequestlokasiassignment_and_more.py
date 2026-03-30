from django.db import migrations, models
import django.db.models.deletion


def migrate_request_pelaksana_to_lokasi_assignments(apps, schema_editor):
    DocumentationRequest = apps.get_model("products", "DocumentationRequest")
    DocumentationRequestLokasiAssignment = apps.get_model("products", "DocumentationRequestLokasiAssignment")

    db_alias = schema_editor.connection.alias
    lokasi_through = DocumentationRequest.lokasi.through
    pelaksana_through = DocumentationRequest.pelaksana.through

    lokasi_map = {}
    for row in lokasi_through.objects.using(db_alias).all():
        lokasi_map.setdefault(row.documentationrequest_id, []).append(row.lokasi_id)

    pelaksana_map = {}
    for row in pelaksana_through.objects.using(db_alias).all():
        pelaksana_map.setdefault(row.documentationrequest_id, []).append(row.dokumentator_id)

    for documentation_request in DocumentationRequest.objects.using(db_alias).all().iterator():
        lokasi_ids = lokasi_map.get(documentation_request.id, [])
        pelaksana_ids = pelaksana_map.get(documentation_request.id, [])

        for lokasi_id in lokasi_ids:
            assignment, _ = DocumentationRequestLokasiAssignment.objects.using(db_alias).get_or_create(
                documentation_request_id=documentation_request.id,
                lokasi_id=lokasi_id,
            )
            if pelaksana_ids:
                assignment.pelaksana.set(pelaksana_ids)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0013_documentationrequest_jenis_lokasi_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentationRequestLokasiAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "documentation_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lokasi_assignments",
                        to="products.documentationrequest",
                    ),
                ),
                (
                    "lokasi",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="doc_request_assignments",
                        to="products.lokasi",
                    ),
                ),
                (
                    "pelaksana",
                    models.ManyToManyField(
                        blank=True,
                        related_name="doc_request_lokasi_assignments",
                        to="products.dokumentator",
                        verbose_name="Pelaksana Dokumentasi",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assignment Lokasi Documentation Request",
                "verbose_name_plural": "Assignment Lokasi Documentation Request",
                "ordering": ["lokasi__name", "id"],
                "unique_together": {("documentation_request", "lokasi")},
            },
        ),
        migrations.RunPython(
            migrate_request_pelaksana_to_lokasi_assignments,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="documentationrequest",
            name="pelaksana",
        ),
    ]
