from django import forms
from .models import DocumentationRequest, MaintenanceRequest, InventoryItem


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
            "brand_materi": forms.Select(attrs={"class": "form-select select2-field"}),
            "lokasi": forms.SelectMultiple(attrs={"class": "form-select select2-field select2-tags", "multiple": "multiple"}),
            "jenis_led": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "tanggal": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "requirements": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "view_photo": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "jenis_kamera": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Add any special requirements or notes here..."}),
            "pic_pemohon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nama / Divisi Pemohon"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand_materi"].queryset = self.fields["brand_materi"].queryset.order_by("name")
        self.fields["lokasi"].queryset = self.fields["lokasi"].queryset.order_by("name")
        self.fields["jenis_led"].queryset = self.fields["jenis_led"].queryset.order_by("name")
        self.fields["requirements"].queryset = self.fields["requirements"].queryset.order_by("name")
        self.fields["view_photo"].queryset = self.fields["view_photo"].queryset.order_by("name")
        self.fields["jenis_kamera"].queryset = self.fields["jenis_kamera"].queryset.order_by("name")


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "nama_pemohon",
            "departement",
            "tanggal_permintaan",
            "tanggal_deadline",
            "nama_perangkat",
            "inventory_items",
            "deskripsi_pekerjaan",
            "foto_kerusakan",
        ]
        widgets = {
            "nama_pemohon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nama lengkap pemohon"}),
            "departement": forms.TextInput(attrs={"class": "form-control", "placeholder": "Departement pemohon"}),
            "tanggal_permintaan": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "tanggal_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "nama_perangkat": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "inventory_items": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "deskripsi_pekerjaan": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Jelaskan detail pekerjaan maintenance / troubleshoot..."}),
            "foto_kerusakan": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['foto_kerusakan'].required = False

    def clean_foto_kerusakan(self):
        foto = self.cleaned_data.get("foto_kerusakan")
        if foto and hasattr(foto, 'size'):
            if foto.size > 10 * 1024 * 1024:  # 10 MB
                raise forms.ValidationError("Ukuran file maksimal 10 MB.")
        return foto


class MasterDataForm(forms.Form):
    """Generic form for simple name-only master data models."""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter name",
        }),
    )
