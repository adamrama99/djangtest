from datetime import date, timedelta
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import DocumentationRequestForm
from .models import (
    BrandMateri,
    DocumentationRequest,
    DocumentationRequestLokasiAssignment,
    Dokumentator,
    EditHistory,
    JadwalTayang,
    LEDType,
    Lokasi,
    Requirement,
    ViewPhoto,
    cameratype,
)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class DocumentationRequestMultiLokasiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        cls.user = get_user_model().objects.create_user(
            username="staff",
            password="password123",
        )
        cls.brand = BrandMateri.objects.create(name="Brand A")
        cls.lokasi_a = Lokasi.objects.create(name="Lokasi A")
        cls.lokasi_b = Lokasi.objects.create(name="Lokasi B")
        cls.led_type = LEDType.objects.create(name="Indoor")
        cls.requirement = Requirement.objects.create(name="Foto")
        cls.view_photo = ViewPhoto.objects.create(name="Close Up")
        cls.camera_type = cameratype.objects.create(name="Sony")
        cls.dokumentator_a = Dokumentator.objects.create(name="Dokumentator A")
        cls.dokumentator_b = Dokumentator.objects.create(name="Dokumentator B")

    def get_form_data(self, **overrides):
        data = {
            "brand_materi": str(self.brand.id),
            "lokasi": [str(self.lokasi_a.id)],
            "jenis_led": str(self.led_type.id),
            "tanggal": date.today().isoformat(),
            "requirements": [str(self.requirement.id)],
            "view_photo": [str(self.view_photo.id)],
            "jenis_kamera": [str(self.camera_type.id)],
            "note": "Catatan test",
            "pic_pemohon": "Marketing",
        }
        data.update(overrides)
        return data

    def create_doc_request(self):
        doc_request = DocumentationRequest.objects.create(
            submitted_by=self.user,
            brand_materi=self.brand,
            jenis_led=self.led_type,
            tanggal=date.today(),
            note="Catatan test",
            pic_pemohon="Marketing",
        )
        doc_request.lokasi.set([self.lokasi_a, self.lokasi_b])
        doc_request.requirements.set([self.requirement])
        doc_request.view_photo.set([self.view_photo])
        doc_request.jenis_kamera.set([self.camera_type])
        return doc_request

    def test_form_valid_with_multiple_selected_locations(self):
        form = DocumentationRequestForm(
            data=self.get_form_data(
                lokasi=[str(self.lokasi_a.id), str(self.lokasi_b.id)],
            )
        )

        self.assertTrue(form.is_valid())

    def test_create_view_splits_selected_locations_into_multiple_requests(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("doc_request_create"),
            data=self.get_form_data(
                lokasi=[str(self.lokasi_a.id), str(self.lokasi_b.id)],
            ),
        )

        created_requests = list(DocumentationRequest.objects.order_by("id"))

        self.assertRedirects(response, reverse("doc_request_list"))
        self.assertEqual(len(created_requests), 2)
        self.assertEqual(
            sorted(doc_request.lokasi_display() for doc_request in created_requests),
            ["Lokasi A", "Lokasi B"],
        )
        for doc_request in created_requests:
            self.assertEqual(doc_request.lokasi.count(), 1)
            self.assertEqual(doc_request.lokasi_assignments.count(), 1)

    def test_dashboard_list_and_detail_pages_render_with_multi_lokasi(self):
        doc_request = self.create_doc_request()
        self.client.force_login(self.user)

        dashboard_response = self.client.get(reverse("dashboard"))
        list_response = self.client.get(reverse("doc_request_list"))
        detail_response = self.client.get(reverse("doc_request_detail", args=[doc_request.pk]))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(list_response, "Lokasi A, Lokasi B")
        self.assertContains(detail_response, "Lokasi A, Lokasi B")

    def test_lokasi_assignments_created_when_locations_are_set(self):
        doc_request = self.create_doc_request()

        assignments = DocumentationRequestLokasiAssignment.objects.filter(
            documentation_request=doc_request
        ).order_by("lokasi__name")

        self.assertEqual(assignments.count(), 2)
        self.assertEqual(assignments[0].lokasi, self.lokasi_a)
        self.assertEqual(assignments[1].lokasi, self.lokasi_b)

    def test_admin_can_assign_pelaksana_per_location(self):
        doc_request = self.create_doc_request()
        assignment_a = doc_request.lokasi_assignments.get(lokasi=self.lokasi_a)
        assignment_b = doc_request.lokasi_assignments.get(lokasi=self.lokasi_b)
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("doc_request_update_lokasi_pelaksana", args=[assignment_a.pk]),
            {"pelaksana[]": [self.dokumentator_a.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        assignment_a.refresh_from_db()
        assignment_b.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            assignment_a.pelaksana.order_by("name").values_list("name", flat=True),
            ["Dokumentator A"],
            transform=lambda value: value,
        )
        self.assertFalse(assignment_b.pelaksana.exists())

    def test_detail_page_shows_assignment_per_location(self):
        doc_request = self.create_doc_request()
        assignment_a = doc_request.lokasi_assignments.get(lokasi=self.lokasi_a)
        assignment_b = doc_request.lokasi_assignments.get(lokasi=self.lokasi_b)
        assignment_a.pelaksana.set([self.dokumentator_a])
        assignment_b.pelaksana.set([self.dokumentator_b])
        self.client.force_login(self.user)

        response = self.client.get(reverse("doc_request_detail", args=[doc_request.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dokumentator A")
        self.assertContains(response, "Dokumentator B")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class JadwalTayangHistoryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="admin_jt",
            email="admin_jt@example.com",
            password="password123",
        )
        cls.brand = BrandMateri.objects.create(name="Brand JT")
        cls.lokasi_a = Lokasi.objects.create(name="Lokasi JT A")
        cls.lokasi_b = Lokasi.objects.create(name="Lokasi JT B")
        cls.led_type = LEDType.objects.create(name="Outdoor JT")
        cls.dokumentator_a = Dokumentator.objects.create(name="Dokumentator JT A")
        cls.dokumentator_b = Dokumentator.objects.create(name="Dokumentator JT B")

    def _datetime_input(self, value):
        return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")

    def _upload_file(self, name):
        return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/jpeg")

    def create_jadwal_tayang(self):
        start_at = timezone.now()
        jadwal_tayang = JadwalTayang.objects.create(
            submitted_by=self.admin,
            brand_materi=self.brand,
            jenis_led=self.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=start_at + timedelta(hours=6),
            note_requester="Catatan requester",
            pic_pemohon="Marketing",
        )
        jadwal_tayang.lokasi.set([self.lokasi_a])
        return jadwal_tayang

    def test_create_view_logs_history_for_each_created_location(self):
        self.client.force_login(self.admin)
        start_at = timezone.now()

        response = self.client.post(
            reverse("jadwal_tayang_create"),
            data={
                "brand_materi": str(self.brand.id),
                "lokasi": [str(self.lokasi_a.id), str(self.lokasi_b.id)],
                "jenis_led": str(self.led_type.id),
                "tanggal_tayang": self._datetime_input(start_at),
                "tanggal_takeout": self._datetime_input(start_at + timedelta(hours=6)),
                "note_requester": "Catatan requester",
                "pic_pemohon": "Marketing",
            },
        )

        history_entries = EditHistory.objects.filter(
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            action="CREATE",
        ).order_by("doc_request_id")

        self.assertRedirects(response, reverse("jadwal_tayang_list"))
        self.assertEqual(JadwalTayang.objects.count(), 2)
        self.assertEqual(history_entries.count(), 2)
        self.assertEqual(
            list(history_entries.values_list("new_value", flat=True)),
            [
                "Jadwal tayang baru dibuat untuk lokasi Lokasi JT A",
                "Jadwal tayang baru dibuat untuk lokasi Lokasi JT B",
            ],
        )

        history_page = self.client.get(reverse("edit_history_list"))
        for history_entry in history_entries:
            self.assertContains(
                history_page,
                reverse("jadwal_tayang_detail", args=[history_entry.doc_request_id]),
            )

    def test_status_and_pelaksana_updates_are_logged(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.admin)

        status_response = self.client.post(
            reverse("jadwal_tayang_update_status", args=[jadwal_tayang.pk]),
            {"status": "SEDANG_TAYANG"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        pelaksana_response = self.client.post(
            reverse("jadwal_tayang_update_pelaksana", args=[jadwal_tayang.pk]),
            {"pelaksana[]": [self.dokumentator_b.pk, self.dokumentator_a.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        status_history = EditHistory.objects.get(
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            doc_request_id=jadwal_tayang.pk,
            field_name="Status",
        )
        pelaksana_history = EditHistory.objects.get(
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            doc_request_id=jadwal_tayang.pk,
            field_name="Pelaksana",
        )

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(pelaksana_response.status_code, 200)
        self.assertEqual(status_history.old_value, "Belum Tayang")
        self.assertEqual(status_history.new_value, "Sedang Tayang")
        self.assertEqual(
            pelaksana_history.new_value,
            "Dokumentator JT A, Dokumentator JT B",
        )

    def test_upload_view_logs_note_files_and_auto_status(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("jadwal_tayang_upload_photos", args=[jadwal_tayang.pk]),
            data={
                "note_executor": "Catatan executor",
                "foto_tayang": self._upload_file("tayang.jpg"),
                "foto_playlist_pagi": self._upload_file("playlist.jpg"),
                "foto_takeout": self._upload_file("takeout.jpg"),
            },
        )

        history_entries = EditHistory.objects.filter(
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            doc_request_id=jadwal_tayang.pk,
        )
        field_names = set(history_entries.values_list("field_name", flat=True))
        status_history = history_entries.get(field_name="Status")

        self.assertRedirects(response, reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]))
        self.assertSetEqual(
            field_names,
            {"Notes Executor", "Foto Tayang", "Bukti Playlist", "Foto Takeout", "Status"},
        )
        self.assertEqual(status_history.old_value, "Belum Tayang")
        self.assertEqual(status_history.new_value, "Sudah Takeout")

    def test_delete_logs_history(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.admin)

        response = self.client.post(reverse("jadwal_tayang_delete", args=[jadwal_tayang.pk]))

        history_entry = EditHistory.objects.get(
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            action="DELETE",
        )

        self.assertRedirects(response, reverse("jadwal_tayang_list"))
        self.assertFalse(JadwalTayang.objects.filter(pk=jadwal_tayang.pk).exists())
        self.assertEqual(history_entry.doc_request_id, jadwal_tayang.pk)
        self.assertEqual(history_entry.new_value, "Dihapus")
