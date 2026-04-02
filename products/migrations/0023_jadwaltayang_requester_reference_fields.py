from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0022_takeoutalertrule_trigger_direction"),
    ]

    operations = [
        migrations.AddField(
            model_name="jadwaltayang",
            name="foto_referensi_requester",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="jadwal_tayang/requester/",
                verbose_name="Foto Referensi Requester",
            ),
        ),
        migrations.AddField(
            model_name="jadwaltayang",
            name="link_foto_drive_requester",
            field=models.URLField(blank=True, verbose_name="Link Foto Google Drive"),
        ),
    ]
