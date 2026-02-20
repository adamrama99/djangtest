from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    description = models.TextField(blank=True)

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

class DocumentationRequest(models.Model):
    email = models.EmailField()
    brand_materi = models.CharField("Brand / Materi", max_length=200)
    lokasi = models.CharField("Lokasi", max_length=200)
    jenis_led = models.ForeignKey(LEDType, on_delete=models.SET_NULL, null=True, verbose_name="Jenis LED")
    tanggal = models.DateField()
    requirements = models.ManyToManyField(Requirement, verbose_name="Requirements")
    view_photo = models.ManyToManyField(ViewPhoto, verbose_name="View Photo")
    jenis_kamera = models.ManyToManyField(cameratype, verbose_name="Jenis Kamera")
    note = models.TextField(blank=True)
    pic_pemohon = models.CharField("PIC Pemohon", max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand_materi} - {self.tanggal}"