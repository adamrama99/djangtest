from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from .models import (
    DocumentationRequest,
    MaintenanceRequest,
    JadwalTayang,
    Lokasi,
    TakeoutAlertRule,
    UserLoginRequirement,
)

User = get_user_model()


def _validate_image_size(foto):
    if foto and hasattr(foto, "size") and foto.size > 10 * 1024 * 1024:
        raise forms.ValidationError("Ukuran file maksimal 10 MB.")
    return foto

class DocumentationRequestForm(forms.ModelForm):
    class Meta:
        model = DocumentationRequest
        fields = [
            "brand",
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
            "brand": forms.Select(attrs={"class": "form-select select2-field"}),
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
        self.fields["brand"].queryset = self.fields["brand"].queryset.order_by("name")
        self.fields["lokasi"].queryset = self.fields["lokasi"].queryset.order_by("name")
        self.fields["jenis_led"].queryset = self.fields["jenis_led"].queryset.order_by("name")
        self.fields["requirements"].queryset = self.fields["requirements"].queryset.order_by("name")
        self.fields["view_photo"].queryset = self.fields["view_photo"].queryset.order_by("name")
        self.fields["jenis_kamera"].queryset = self.fields["jenis_kamera"].queryset.order_by("name")


class DocumentationRequestEditForm(DocumentationRequestForm):
    lokasi = forms.ModelChoiceField(
        queryset=Lokasi.objects.none(),
        widget=forms.Select(attrs={"class": "form-select select2-field select2-tags"}),
        label="Lokasi",
    )

    class Meta(DocumentationRequestForm.Meta):
        widgets = {
            **DocumentationRequestForm.Meta.widgets,
            "lokasi": forms.Select(attrs={"class": "form-select select2-field select2-tags"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lokasi"].queryset = Lokasi.objects.order_by("name")
        if self.instance and self.instance.pk:
            self.initial["lokasi"] = self.instance.lokasi.order_by("name").first()


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "nama_pemohon",
            "departement",
            "tanggal_permintaan",
            "tanggal_deadline",
            "brand",
            "lokasi",
            "jenis_led",
            "deskripsi_pekerjaan",
            "foto_kerusakan",
        ]
        widgets = {
            "nama_pemohon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nama lengkap pemohon"}),
            "departement": forms.TextInput(attrs={"class": "form-control", "placeholder": "Departement pemohon"}),
            "tanggal_permintaan": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "tanggal_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "brand": forms.Select(attrs={"class": "form-select select2-field"}),
            "lokasi": forms.SelectMultiple(attrs={"class": "form-select select2-field select2-tags", "multiple": "multiple"}),
            "jenis_led": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "deskripsi_pekerjaan": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Jelaskan detail pekerjaan maintenance / troubleshoot..."}),
            "foto_kerusakan": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = self.fields["brand"].queryset.order_by("name")
        self.fields["lokasi"].queryset = self.fields["lokasi"].queryset.order_by("name")
        self.fields["jenis_led"].queryset = self.fields["jenis_led"].queryset.order_by("name")
        self.fields["brand"].required = True
        self.fields["lokasi"].required = True
        self.fields["jenis_led"].label = "Jenis Produk"
        self.fields["foto_kerusakan"].required = False

    def clean_foto_kerusakan(self):
        return _validate_image_size(self.cleaned_data.get("foto_kerusakan"))


class MaintenanceRequestEditForm(MaintenanceRequestForm):
    lokasi = forms.ModelChoiceField(
        queryset=Lokasi.objects.none(),
        widget=forms.Select(attrs={"class": "form-select select2-field select2-tags"}),
        label="Lokasi",
    )

    class Meta(MaintenanceRequestForm.Meta):
        widgets = {
            **MaintenanceRequestForm.Meta.widgets,
            "lokasi": forms.Select(attrs={"class": "form-select select2-field select2-tags"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lokasi"].queryset = Lokasi.objects.order_by("name")
        if self.instance and self.instance.pk:
            self.initial["lokasi"] = self.instance.lokasi.order_by("name").first()


class DocumentationRequestProofForm(forms.ModelForm):
    class Meta:
        model = DocumentationRequest
        fields = ["foto_bukti_kerja"]
        widgets = {
            "foto_bukti_kerja": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["foto_bukti_kerja"].required = True

    def clean_foto_bukti_kerja(self):
        return _validate_image_size(self.cleaned_data.get("foto_bukti_kerja"))


class MaintenanceRequestProofForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["foto_bukti_kerja"]
        widgets = {
            "foto_bukti_kerja": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["foto_bukti_kerja"].required = True

    def clean_foto_bukti_kerja(self):
        return _validate_image_size(self.cleaned_data.get("foto_bukti_kerja"))


class MasterDataForm(forms.Form):
    """Generic form for simple name-only master data models."""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter name",
        }),
    )


class JadwalTayangForm(forms.ModelForm):
    class Meta:
        model = JadwalTayang
        fields = [
            "brand",
            "lokasi",
            "jenis_led",
            "tanggal_tayang",
            "tanggal_takeout",
            "note_requester",
            "pic_pemohon",
        ]
        widgets = {
            "brand": forms.Select(attrs={"class": "form-select select2-field"}),
            "lokasi": forms.SelectMultiple(attrs={"class": "form-select select2-field select2-tags", "multiple": "multiple"}),
            "jenis_led": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "tanggal_tayang": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "tanggal_takeout": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "note_requester": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Catatan dari pemohon..."}),
            "pic_pemohon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nama / Divisi Pemohon"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = self.fields["brand"].queryset.order_by("name")
        self.fields["lokasi"].queryset = self.fields["lokasi"].queryset.order_by("name")
        self.fields["jenis_led"].queryset = self.fields["jenis_led"].queryset.order_by("name")
        for field_name in ("tanggal_tayang", "tanggal_takeout"):
            self.fields[field_name].input_formats = ["%Y-%m-%dT%H:%M"]
            self.fields[field_name].widget.format = "%Y-%m-%dT%H:%M"
            if not self.is_bound and self.instance and self.instance.pk:
                value = getattr(self.instance, field_name, None)
                if value:
                    self.initial[field_name] = timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")


class JadwalTayangEditForm(JadwalTayangForm):
    lokasi = forms.ModelChoiceField(
        queryset=Lokasi.objects.none(),
        widget=forms.Select(attrs={"class": "form-select select2-field"}),
        label="Lokasi",
    )

    class Meta(JadwalTayangForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lokasi"].queryset = Lokasi.objects.order_by("name")
        if self.instance and self.instance.pk:
            self.initial["lokasi"] = self.instance.lokasi.order_by("name").first()


class TakeoutAlertRuleForm(forms.ModelForm):
    class Meta:
        model = TakeoutAlertRule
        fields = ["name", "trigger_direction", "offset_unit", "offset_value", "urgency", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Contoh: H-1 Warning atau Jam+2 Urgent"}),
            "trigger_direction": forms.Select(attrs={"class": "form-select"}),
            "offset_unit": forms.Select(attrs={"class": "form-select"}),
            "offset_value": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "urgency": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = "Nama aturan untuk memudahkan identifikasi."
        self.fields["trigger_direction"].help_text = "Pilih apakah rule aktif sebelum atau sesudah waktu takeout."
        self.fields["offset_unit"].help_text = "Pilih apakah trigger dihitung dalam hari atau jam."
        self.fields["offset_value"].help_text = "Isi 0 untuk tepat di waktu takeout, 1 untuk H-1/H+1, atau 6 untuk Jam-6/Jam+6."
        self.fields["urgency"].help_text = "Urgent akan muncul di bell dan popup berulang."

    def clean_offset_value(self):
        value = self.cleaned_data["offset_value"]
        if value < 0:
            raise forms.ValidationError("Nilai offset minimal 0.")
        return value


class UserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Leave blank to keep current password"}),
        help_text="Kosongkan jika tidak ingin mengubah password.",
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Role",
    )
    requires_login = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Perlu Login",
        help_text="Matikan untuk akun yang tidak wajib login agar tidak muncul di halaman user belum pernah login.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "requires_login", "groups"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["password"].help_text = "Kosongkan jika tidak ingin mengubah password."
            login_requirement = UserLoginRequirement.objects.filter(user=self.instance).first()
            self.initial.setdefault(
                "requires_login",
                login_requirement.requires_login if login_requirement else True,
            )
        else:
            self.fields["password"].required = True
            self.fields["password"].widget.attrs["placeholder"] = "Enter password"

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self.save_m2m()
            UserLoginRequirement.objects.update_or_create(
                user=user,
                defaults={"requires_login": self.cleaned_data.get("requires_login", False)},
            )
        return user
