from django.db import models
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
    lokasi = models.ForeignKey(Lokasi, on_delete=models.SET_NULL, null=True, verbose_name="Lokasi")
    jenis_led = models.ForeignKey(LEDType, on_delete=models.SET_NULL, null=True, verbose_name="Jenis LED")
    tanggal = models.DateField()
    requirements = models.ManyToManyField(Requirement, verbose_name="Requirements")
    view_photo = models.ManyToManyField(ViewPhoto, verbose_name="View Photo")
    jenis_kamera = models.ManyToManyField(cameratype, verbose_name="Jenis Kamera")
    pelaksana = models.ManyToManyField('Dokumentator', blank=True, verbose_name="Pelaksana Dokumentasi")
    note = models.TextField(blank=True)
    pic_pemohon = models.CharField("PIC Pemohon", max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        brand = self.brand_materi.name if self.brand_materi else "N/A"
        return f"{brand} - {self.tanggal}"


class EditHistory(models.Model):
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