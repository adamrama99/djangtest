from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.conf import settings


class BrandMateri(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class Lokasi(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class cameratype(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class LEDType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Requirement(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ViewPhoto(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Dokumentator(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class DocumentationRequest(models.Model):
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'On Progress'),
        ('DONE', 'Done'),
    ]

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doc_requests",
        verbose_name="Submitted By",
    )
    brand_materi = models.ForeignKey(BrandMateri, on_delete=models.SET_NULL, null=True, verbose_name="Brand / Materi")
    lokasi = models.ManyToManyField(Lokasi, verbose_name="Lokasi")
    jenis_led = models.ForeignKey(LEDType, on_delete=models.SET_NULL, null=True, verbose_name="Jenis Produk")
    tanggal = models.DateField()
    requirements = models.ManyToManyField(Requirement, verbose_name="Requirements")
    view_photo = models.ManyToManyField(ViewPhoto, verbose_name="View Photo")
    jenis_kamera = models.ManyToManyField(cameratype, verbose_name="Jenis Kamera")
    note = models.TextField(blank=True)
    pic_pemohon = models.CharField("PIC Pemohon", max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        brand = self.brand_materi.name if self.brand_materi else "N/A"
        return f"{brand} - {self.tanggal}"

    def lokasi_names(self):
        return list(self.lokasi.order_by("name").values_list("name", flat=True))

    def lokasi_display(self):
        lokasi_names = self.lokasi_names()
        return ", ".join(lokasi_names) if lokasi_names else "-"

    def sync_lokasi_assignments(self):
        lokasi_ids = list(self.lokasi.values_list("id", flat=True))
        self.lokasi_assignments.exclude(lokasi_id__in=lokasi_ids).delete()

        existing_lokasi_ids = set(self.lokasi_assignments.values_list("lokasi_id", flat=True))
        DocumentationRequestLokasiAssignment.objects.bulk_create(
            [
                DocumentationRequestLokasiAssignment(
                    documentation_request=self,
                    lokasi_id=lokasi_id,
                )
                for lokasi_id in lokasi_ids
                if lokasi_id not in existing_lokasi_ids
            ]
        )


class DocumentationRequestLokasiAssignment(models.Model):
    documentation_request = models.ForeignKey(
        DocumentationRequest,
        on_delete=models.CASCADE,
        related_name="lokasi_assignments",
    )
    lokasi = models.ForeignKey(
        Lokasi,
        on_delete=models.CASCADE,
        related_name="doc_request_assignments",
    )
    pelaksana = models.ManyToManyField(
        Dokumentator,
        blank=True,
        related_name="doc_request_lokasi_assignments",
        verbose_name="Pelaksana Dokumentasi",
    )

    class Meta:
        unique_together = ("documentation_request", "lokasi")
        ordering = ["lokasi__name", "id"]
        verbose_name = "Assignment Lokasi Documentation Request"
        verbose_name_plural = "Assignment Lokasi Documentation Request"

    def __str__(self):
        return f"{self.documentation_request} - {self.lokasi}"

    def pelaksana_names(self):
        return list(self.pelaksana.order_by("name").values_list("name", flat=True))

    def pelaksana_display(self):
        names = self.pelaksana_names()
        return ", ".join(names) if names else "Belum ditentukan"


class EditHistory(models.Model):
    class RequestType(models.TextChoices):
        DOC_REQUEST = "DOC_REQUEST", "Documentation Request"
        JADWAL_TAYANG = "JADWAL_TAYANG", "Jadwal Tayang"

    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="edit_history",
    )
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.DOC_REQUEST,
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    doc_request_id = models.IntegerField(null=True, blank=True)
    doc_request_label = models.CharField(max_length=255, blank=True)
    field_name = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} – {self.get_action_display()} – {self.doc_request_label}"


    @property
    def detail_url_name(self):
        if self.request_type == self.RequestType.JADWAL_TAYANG:
            return "jadwal_tayang_detail"
        return "doc_request_detail"


class NamaPerangkat(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    GROUP_CHOICES = [
        ('MING', 'Inventory MING'),
        ('MOBILE_LED', 'Inventory Mobile LED'),
        ('MST', 'Inventory MST'),
        ('LUMINOVA', 'Inventory Luminova'),
    ]
    name = models.CharField(max_length=150)
    group = models.CharField(max_length=20, choices=GROUP_CHOICES)

    class Meta:
        unique_together = ('name', 'group')
        ordering = ['group', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_group_display()})"


class MaintenanceRequest(models.Model):
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'On Progress'),
        ('DONE', 'Done'),
    ]

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="maint_requests",
        verbose_name="Submitted By",
    )
    nama_pemohon = models.CharField("Nama Pemohon", max_length=150)
    departement = models.CharField("Departement", max_length=150)
    tanggal_permintaan = models.DateField("Tanggal Permintaan")
    tanggal_deadline = models.DateField("Tanggal Deadline")
    nama_perangkat = models.ManyToManyField(NamaPerangkat, verbose_name="Nama Perangkat")
    inventory_items = models.ManyToManyField(InventoryItem, blank=True, verbose_name="Inventory")
    deskripsi_pekerjaan = models.TextField("Deskripsi Pekerjaan")
    foto_kerusakan = models.ImageField("Foto Kerusakan", upload_to="maintenance_photos/", blank=True, null=True)
    pelaksana = models.ManyToManyField('Dokumentator', blank=True, verbose_name="Pelaksana Maintenance")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama_pemohon} - {self.tanggal_permintaan}"


class JadwalTayang(models.Model):
    STATUS_CHOICES = [
        ('BELUM_TAYANG', 'Belum Tayang'),
        ('SEDANG_TAYANG', 'Sedang Tayang'),
        ('SUDAH_TAKEOUT', 'Sudah Takeout'),
    ]

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jadwal_tayang_requests",
        verbose_name="Submitted By",
    )
    brand_materi = models.ForeignKey(
        BrandMateri, on_delete=models.SET_NULL, null=True,
        verbose_name="Brand / Materi",
    )
    lokasi = models.ManyToManyField(Lokasi, verbose_name="Lokasi")
    jenis_led = models.ForeignKey(
        LEDType, on_delete=models.SET_NULL, null=True,
        verbose_name="Jenis Produk",
    )
    tanggal_tayang = models.DateTimeField("Tanggal Tayang")
    tanggal_takeout = models.DateTimeField("Tanggal Takeout")
    note_requester = models.TextField("Notes Requester", blank=True)
    note_executor = models.TextField("Notes Executor", blank=True)
    pic_pemohon = models.CharField("PIC Pemohon", max_length=150)
    pelaksana = models.ManyToManyField(
        Dokumentator, blank=True,
        related_name="jadwal_tayang_assignments",
        verbose_name="Pelaksana",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BELUM_TAYANG')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        brand = self.brand_materi.name if self.brand_materi else "N/A"
        return f"{brand} - {self.tanggal_tayang}"

    def auto_update_status(self):
        """Auto-set status based on uploaded photos."""
        has_foto_takeout = self.foto_takeout_set.exists()
        has_foto_tayang = self.foto_tayang_set.exists()
        if has_foto_takeout:
            new_status = 'SUDAH_TAKEOUT'
        elif has_foto_tayang:
            new_status = 'SEDANG_TAYANG'
        else:
            new_status = 'BELUM_TAYANG'
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])

    def lokasi_names(self):
        return list(self.lokasi.order_by("name").values_list("name", flat=True))

    def lokasi_display(self):
        names = self.lokasi_names()
        return ", ".join(names) if names else "-"


class JadwalTayangFotoTayang(models.Model):
    jadwal_tayang = models.ForeignKey(
        JadwalTayang, on_delete=models.CASCADE,
        related_name="foto_tayang_set",
    )
    foto = models.ImageField("Foto Tayang", upload_to="jadwal_tayang/tayang/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Foto Tayang #{self.pk} - {self.jadwal_tayang}"


class JadwalTayangBuktiPlaylist(models.Model):
    jadwal_tayang = models.OneToOneField(
        JadwalTayang, on_delete=models.CASCADE,
        related_name="bukti_playlist",
    )
    foto_pagi = models.ImageField(
        "Bukti Playlist Pagi", upload_to="jadwal_tayang/playlist/",
        blank=True, null=True,
    )
    foto_siang = models.ImageField(
        "Bukti Playlist Siang", upload_to="jadwal_tayang/playlist/",
        blank=True, null=True,
    )
    foto_malam = models.ImageField(
        "Bukti Playlist Malam", upload_to="jadwal_tayang/playlist/",
        blank=True, null=True,
    )
    uploaded_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bukti Playlist - {self.jadwal_tayang}"


class JadwalTayangFotoTakeout(models.Model):
    jadwal_tayang = models.ForeignKey(
        JadwalTayang, on_delete=models.CASCADE,
        related_name="foto_takeout_set",
    )
    foto = models.ImageField("Foto Takeout", upload_to="jadwal_tayang/takeout/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Foto Takeout #{self.pk} - {self.jadwal_tayang}"


class TakeoutAlertRule(models.Model):
    class OffsetUnit(models.TextChoices):
        DAY = "DAY", "Hari"
        HOUR = "HOUR", "Jam"

    class Urgency(models.TextChoices):
        WARNING = "WARNING", "Warning"
        URGENT = "URGENT", "Urgent"

    name = models.CharField(max_length=150, unique=True)
    offset_unit = models.CharField(max_length=10, choices=OffsetUnit.choices)
    offset_value = models.PositiveIntegerField()
    lead_minutes = models.PositiveIntegerField(default=0, editable=False)
    urgency = models.CharField(max_length=10, choices=Urgency.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-lead_minutes", "urgency", "name"]
        verbose_name = "Takeout Alert Rule"
        verbose_name_plural = "Takeout Alert Rules"

    def __str__(self):
        return f"{self.name} ({self.offset_display()} - {self.get_urgency_display()})"

    def save(self, *args, **kwargs):
        multiplier = 1440 if self.offset_unit == self.OffsetUnit.DAY else 60
        self.lead_minutes = self.offset_value * multiplier
        super().save(*args, **kwargs)

    def offset_display(self):
        if self.offset_unit == self.OffsetUnit.DAY:
            return f"H-{self.offset_value}"
        return f"Jam-{self.offset_value}"


@receiver(m2m_changed, sender=DocumentationRequest.lokasi.through)
def sync_doc_request_lokasi_assignments(sender, instance, action, reverse, **kwargs):
    if reverse or not instance.pk:
        return

    if action in {"post_add", "post_remove", "post_clear"}:
        instance.sync_lokasi_assignments()
