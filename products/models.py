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