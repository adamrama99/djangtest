from django.db import migrations, models


def sync_existing_materi_statuses(apps, schema_editor):
    JadwalTayang = apps.get_model("products", "JadwalTayang")
    JadwalTayangMateri = apps.get_model("products", "JadwalTayangMateri")
    JadwalTayangFotoTayang = apps.get_model("products", "JadwalTayangFotoTayang")
    JadwalTayangFotoTakeout = apps.get_model("products", "JadwalTayangFotoTakeout")
    JadwalTayangBuktiPlaylist = apps.get_model("products", "JadwalTayangBuktiPlaylist")

    for materi in JadwalTayangMateri.objects.all().iterator():
        has_takeout = JadwalTayangFotoTakeout.objects.filter(materi_id=materi.id).exists()
        has_tayang = JadwalTayangFotoTayang.objects.filter(materi_id=materi.id).exists()
        bukti_playlist = JadwalTayangBuktiPlaylist.objects.filter(materi_id=materi.id).first()
        has_playlist = bool(
            bukti_playlist
            and (
                bukti_playlist.foto_pagi
                or bukti_playlist.foto_siang
                or bukti_playlist.foto_malam
            )
        )

        if has_takeout:
            materi.status = "SUDAH_TAKEOUT"
        elif has_tayang or has_playlist:
            materi.status = "SEDANG_TAYANG"
        else:
            materi.status = "BELUM_TAYANG"
        materi.save(update_fields=["status"])

    for jadwal_tayang in JadwalTayang.objects.all().iterator():
        statuses = list(
            JadwalTayangMateri.objects.filter(jadwal_tayang_id=jadwal_tayang.id)
            .values_list("status", flat=True)
        )
        if not statuses or "BELUM_TAYANG" in statuses:
            jadwal_tayang.status = "BELUM_TAYANG"
        elif "SEDANG_TAYANG" in statuses:
            jadwal_tayang.status = "SEDANG_TAYANG"
        else:
            jadwal_tayang.status = "SUDAH_TAKEOUT"
        jadwal_tayang.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0030_jadwaltayang_materi_uploads"),
    ]

    operations = [
        migrations.AddField(
            model_name="jadwaltayangmateri",
            name="status",
            field=models.CharField(
                choices=[
                    ("BELUM_TAYANG", "Belum Tayang"),
                    ("SEDANG_TAYANG", "Sedang Tayang"),
                    ("SUDAH_TAKEOUT", "Sudah Takeout"),
                ],
                default="BELUM_TAYANG",
                max_length=20,
            ),
        ),
        migrations.RunPython(sync_existing_materi_statuses, migrations.RunPython.noop),
    ]
