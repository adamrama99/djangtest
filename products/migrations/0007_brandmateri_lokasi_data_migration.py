from django.db import migrations, models
import django.db.models.deletion


def migrate_data_forward(apps, schema_editor):
    """Convert existing CharField values into FK references."""
    BrandMateri = apps.get_model('products', 'BrandMateri')
    Lokasi = apps.get_model('products', 'Lokasi')
    DocumentationRequest = apps.get_model('products', 'DocumentationRequest')

    for req in DocumentationRequest.objects.all():
        # Migrate brand_materi
        if req.brand_materi:
            brand, _ = BrandMateri.objects.get_or_create(name=req.brand_materi)
            req.brand_materi_fk = brand

        # Migrate lokasi
        if req.lokasi:
            lokasi, _ = Lokasi.objects.get_or_create(name=req.lokasi)
            req.lokasi_fk = lokasi

        req.save()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_documentationrequest_status'),
    ]

    operations = [
        # Step 1: Create new models
        migrations.CreateModel(
            name='BrandMateri',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Lokasi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
            ],
        ),

        # Step 2: Add temporary FK fields (nullable)
        migrations.AddField(
            model_name='documentationrequest',
            name='brand_materi_fk',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='products.brandmateri',
                verbose_name='Brand / Materi',
            ),
        ),
        migrations.AddField(
            model_name='documentationrequest',
            name='lokasi_fk',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='products.lokasi',
                verbose_name='Lokasi',
            ),
        ),

        # Step 3: Migrate data from old CharFields to new FKs
        migrations.RunPython(migrate_data_forward, migrations.RunPython.noop),

        # Step 4: Remove old CharField columns
        migrations.RemoveField(
            model_name='documentationrequest',
            name='brand_materi',
        ),
        migrations.RemoveField(
            model_name='documentationrequest',
            name='lokasi',
        ),

        # Step 5: Rename FK fields to original names
        migrations.RenameField(
            model_name='documentationrequest',
            old_name='brand_materi_fk',
            new_name='brand_materi',
        ),
        migrations.RenameField(
            model_name='documentationrequest',
            old_name='lokasi_fk',
            new_name='lokasi',
        ),
    ]
