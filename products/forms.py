from django import forms
from .models import Product, DocumentationRequest


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "price", "stock", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product name",
            }),
            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "0.00",
                "step": "0.01",
            }),
            "stock": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "0",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Optional product description...",
            }),
        }

class DocumentationRequestForm(forms.ModelForm):
    class Meta:
        model = DocumentationRequest
        fields = [
            "email",
            "brand_materi",
            "lokasi",
            "jenis_led",
            "tanggal",
            "requirements",
            "view_photo",
            "jenis_kamera",
            "note",
            "pic_pemohon",
        ]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "nama@perusahaan.com"}),
            "brand_materi": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nama Brand / Materi"}),
            "lokasi": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lokasi Pemasangan / Shooting"}),
            "jenis_led": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "tanggal": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "requirements": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "view_photo": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "jenis_kamera": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Add any special requirements or notes here..."}),
            "pic_pemohon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nama / Divisi Pemohon"}),
        }