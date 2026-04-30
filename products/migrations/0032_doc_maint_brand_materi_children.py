import django.db.models.deletion
from django.db import migrations, models


def create_default_materi_rows(apps, schema_editor):
    DocumentationRequest = apps.get_model("products", "DocumentationRequest")
    DocumentationRequestMateri = apps.get_model("products", "DocumentationRequestMateri")
    MaintenanceRequest = apps.get_model("products", "MaintenanceRequest")
    MaintenanceRequestMateri = apps.get_model("products", "MaintenanceRequestMateri")

    DocumentationRequestMateri.objects.bulk_create(
        [
            DocumentationRequestMateri(
                documentation_request_id=doc_request.id,
                nama_materi="Materi 1",
                sort_order=0,
            )
            for doc_request in DocumentationRequest.objects.all().only("id")
        ]
    )
    MaintenanceRequestMateri.objects.bulk_create(
        [
            MaintenanceRequestMateri(
                maintenance_request_id=maint_request.id,
                nama_materi="Materi 1",
                sort_order=0,
            )
            for maint_request in MaintenanceRequest.objects.all().only("id")
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0031_jadwaltayangmateri_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="documentationrequest",
            old_name="brand_materi",
            new_name="brand",
        ),
        migrations.RenameField(
            model_name="maintenancerequest",
            old_name="brand_materi",
            new_name="brand",
        ),
        migrations.AlterField(
            model_name="documentationrequest",
            name="brand",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="products.brandmateri",
                verbose_name="Brand",
            ),
        ),
        migrations.AlterField(
            model_name="maintenancerequest",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="products.brandmateri",
                verbose_name="Brand",
            ),
        ),
        migrations.CreateModel(
            name="DocumentationRequestMateri",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nama_materi", models.CharField(max_length=200, verbose_name="Materi")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "documentation_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materi_items",
                        to="products.documentationrequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Materi Documentation Request",
                "verbose_name_plural": "Materi Documentation Request",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="MaintenanceRequestMateri",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nama_materi", models.CharField(max_length=200, verbose_name="Materi")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "maintenance_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materi_items",
                        to="products.maintenancerequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Materi Maintenance Request",
                "verbose_name_plural": "Materi Maintenance Request",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(create_default_materi_rows, migrations.RunPython.noop),
    ]
