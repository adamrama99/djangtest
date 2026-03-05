from django import forms
from .models import DocumentationRequest

class DocumentationRequestForm(forms.ModelForm):
    class Meta:
        model = DocumentationRequest
        fields = [
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


class MasterDataForm(forms.Form):
    """Generic form for simple name-only master data models."""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter name",
        }),
    )