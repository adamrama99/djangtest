import django.db.models.deletion
from django.db import migrations, models


def migrate_existing_jadwal_photos_to_default_materi(apps, schema_editor):
    JadwalTayang = apps.get_model("products", "JadwalTayang")
    JadwalTayangMateri = apps.get_model("products", "JadwalTayangMateri")
    JadwalTayangFotoTayang = apps.get_model("products", "JadwalTayangFotoTayang")
    JadwalTayangFotoTakeout = apps.get_model("products", "JadwalTayangFotoTakeout")
    JadwalTayangBuktiPlaylist = apps.get_model("products", "JadwalTayangBuktiPlaylist")

    materi_by_jadwal_id = {}
    for jadwal_tayang in JadwalTayang.objects.all().order_by("id"):
        materi = JadwalTayangMateri.objects.create(
            jadwal_tayang_id=jadwal_tayang.id,
            nama_materi="Materi 1",
            sort_order=0,
        )
        materi_by_jadwal_id[jadwal_tayang.id] = materi.id

    def get_materi_id(jadwal_tayang_id):
        materi_id = materi_by_jadwal_id.get(jadwal_tayang_id)
        if materi_id:
            return materi_id
        materi = JadwalTayangMateri.objects.create(
            jadwal_tayang_id=jadwal_tayang_id,
            nama_materi="Materi 1",
            sort_order=0,
        )
        materi_by_jadwal_id[jadwal_tayang_id] = materi.id
        return materi.id

    for foto_tayang in JadwalTayangFotoTayang.objects.all().iterator():
        foto_tayang.materi_id = get_materi_id(foto_tayang.jadwal_tayang_id)
        foto_tayang.save(update_fields=["materi"])

    for foto_takeout in JadwalTayangFotoTakeout.objects.all().iterator():
        foto_takeout.materi_id = get_materi_id(foto_takeout.jadwal_tayang_id)
        foto_takeout.save(update_fields=["materi"])

    for bukti_playlist in JadwalTayangBuktiPlaylist.objects.all().iterator():
        bukti_playlist.materi_id = get_materi_id(bukti_playlist.jadwal_tayang_id)
        bukti_playlist.save(update_fields=["materi"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0029_maintenance_request_use_led_type_master"),
    ]

    operations = [
        migrations.RenameField(
            model_name="jadwaltayang",
            old_name="brand_materi",
            new_name="brand",
        ),
        migrations.AlterField(
            model_name="jadwaltayang",
            name="brand",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="products.brandmateri",
                verbose_name="Brand",
            ),
        ),
        migrations.CreateModel(
            name="JadwalTayangMateri",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nama_materi", models.CharField(max_length=200, verbose_name="Materi")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "jadwal_tayang",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materi_items",
                        to="products.jadwaltayang",
                    ),
                ),
            ],
            options={
                "verbose_name": "Materi Jadwal Tayang",
                "verbose_name_plural": "Materi Jadwal Tayang",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddField(
            model_name="jadwaltayangfototayang",
            name="materi",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="foto_tayang_set",
                to="products.jadwaltayangmateri",
            ),
        ),
        migrations.AddField(
            model_name="jadwaltayangfototakeout",
            name="materi",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="foto_takeout_set",
                to="products.jadwaltayangmateri",
            ),
        ),
        migrations.AddField(
            model_name="jadwaltayangbuktiplaylist",
            name="materi",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bukti_playlist",
                to="products.jadwaltayangmateri",
            ),
        ),
        migrations.RunPython(
            migrate_existing_jadwal_photos_to_default_materi,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="jadwaltayangfototayang",
            name="materi",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="foto_tayang_set",
                to="products.jadwaltayangmateri",
            ),
        ),
        migrations.AlterField(
            model_name="jadwaltayangfototakeout",
            name="materi",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="foto_takeout_set",
                to="products.jadwaltayangmateri",
            ),
        ),
        migrations.AlterField(
            model_name="jadwaltayangbuktiplaylist",
            name="materi",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bukti_playlist",
                to="products.jadwaltayangmateri",
            ),
        ),
        migrations.RemoveField(
            model_name="jadwaltayangfototayang",
            name="jadwal_tayang",
        ),
        migrations.RemoveField(
            model_name="jadwaltayangfototakeout",
            name="jadwal_tayang",
        ),
        migrations.RemoveField(
            model_name="jadwaltayangbuktiplaylist",
            name="jadwal_tayang",
        ),
    ]
