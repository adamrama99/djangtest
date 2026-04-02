from datetime import date, timedelta
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
    MaintenanceRequest,
    JadwalTayang,
    JadwalTayangBuktiPlaylist,
    JadwalTayangFotoTayang,
    JadwalTayangFotoTakeout,
    LEDType,
    Lokasi,
    NamaPerangkat,
    Requirement,
    TakeoutAlertRule,
    ViewPhoto,
    cameratype,
)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class DocumentationRequestMultiLokasiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        requester_group, _ = Group.objects.get_or_create(name="requester")
        cls.admin = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        cls.user = get_user_model().objects.create_user(
            username="staff",
            password="password123",
        )
        cls.user.groups.add(requester_group)
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
class RequestCreationPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.requester_group, _ = Group.objects.get_or_create(name="requester")
        cls.executor_group, _ = Group.objects.get_or_create(name="executor")
        cls.requester = get_user_model().objects.create_user(
            username="requester_only",
            password="password123",
        )
        cls.requester.groups.add(cls.requester_group)
        cls.executor = get_user_model().objects.create_user(
            username="executor_only",
            password="password123",
        )
        cls.executor.groups.add(cls.executor_group)

    def test_executor_cannot_open_doc_and_maintenance_create_pages(self):
        self.client.force_login(self.executor)

        doc_response = self.client.get(reverse("doc_request_create"))
        maint_response = self.client.get(reverse("maint_request_create"))

        self.assertEqual(doc_response.status_code, 403)
        self.assertEqual(maint_response.status_code, 403)

    def test_requester_can_open_doc_and_maintenance_create_pages(self):
        self.client.force_login(self.requester)

        doc_response = self.client.get(reverse("doc_request_create"))
        maint_response = self.client.get(reverse("maint_request_create"))

        self.assertEqual(doc_response.status_code, 200)
        self.assertEqual(maint_response.status_code, 200)

    def test_executor_does_not_see_create_shortcuts(self):
        self.client.force_login(self.executor)

        dashboard_response = self.client.get(reverse("dashboard"))
        doc_list_response = self.client.get(reverse("doc_request_list"))
        maint_list_response = self.client.get(reverse("maint_request_list"))

        self.assertNotContains(dashboard_response, reverse("doc_request_create"))
        self.assertNotContains(dashboard_response, reverse("maint_request_create"))
        self.assertNotContains(dashboard_response, reverse("jadwal_tayang_create"))
        self.assertNotContains(doc_list_response, reverse("doc_request_create"))
        self.assertNotContains(maint_list_response, reverse("maint_request_create"))


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
        cls.admin.first_name = "Admin"
        cls.admin.last_name = "JT"
        cls.admin.save(update_fields=["first_name", "last_name"])
        cls.brand = BrandMateri.objects.create(name="Brand JT")
        cls.brand_b = BrandMateri.objects.create(name="Brand JT B")
        cls.lokasi_a = Lokasi.objects.create(name="Lokasi JT A")
        cls.lokasi_b = Lokasi.objects.create(name="Lokasi JT B")
        cls.led_type = LEDType.objects.create(name="Outdoor JT")
        cls.led_type_b = LEDType.objects.create(name="Indoor JT")
        cls.dokumentator_a = Dokumentator.objects.create(name="Dokumentator JT A")
        cls.dokumentator_b = Dokumentator.objects.create(name="Dokumentator JT B")
        cls.staff = get_user_model().objects.create_user(
            username="staff_jt",
            password="password123",
        )

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
        jadwal_tayang.refresh_from_db()
        status_history = history_entries.get(field_name="Status")

        self.assertRedirects(response, reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]))
        self.assertSetEqual(
            field_names,
            {"Pelaksana", "Notes Executor", "Foto Tayang", "Bukti Playlist", "Foto Takeout", "Status"},
        )
        self.assertQuerySetEqual(
            jadwal_tayang.pelaksana.order_by("name").values_list("name", flat=True),
            ["Admin JT"],
            transform=lambda value: value,
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

    def test_admin_can_edit_jadwal_tayang_and_logs_history(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.admin)
        new_start_at = timezone.now() + timedelta(days=1)

        response = self.client.post(
            reverse("jadwal_tayang_edit", args=[jadwal_tayang.pk]),
            data={
                "brand_materi": str(self.brand_b.id),
                "lokasi": str(self.lokasi_b.id),
                "jenis_led": str(self.led_type_b.id),
                "tanggal_tayang": self._datetime_input(new_start_at),
                "tanggal_takeout": self._datetime_input(new_start_at + timedelta(hours=8)),
                "note_requester": "Catatan requester baru",
                "pic_pemohon": "Sales",
            },
        )

        jadwal_tayang.refresh_from_db()
        history_entries = EditHistory.objects.filter(
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            doc_request_id=jadwal_tayang.pk,
            action="UPDATE",
        )
        field_names = set(history_entries.values_list("field_name", flat=True))

        self.assertRedirects(response, reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]))
        self.assertEqual(jadwal_tayang.brand_materi, self.brand_b)
        self.assertEqual(jadwal_tayang.jenis_led, self.led_type_b)
        self.assertEqual(jadwal_tayang.lokasi_display(), "Lokasi JT B")
        self.assertEqual(jadwal_tayang.pic_pemohon, "Sales")
        self.assertEqual(jadwal_tayang.note_requester, "Catatan requester baru")
        self.assertSetEqual(
            field_names,
            {
                "Brand / Materi",
                "Lokasi",
                "Jenis Produk",
                "Tanggal Tayang",
                "Tanggal Takeout",
                "PIC Pemohon",
                "Notes Requester",
            },
        )

    def test_non_admin_cannot_access_edit_jadwal_tayang(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.staff)

        response = self.client.get(reverse("jadwal_tayang_edit", args=[jadwal_tayang.pk]))

        self.assertEqual(response.status_code, 403)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class JadwalTayangVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="owner_jt",
            password="password123",
        )
        cls.viewer = get_user_model().objects.create_user(
            username="viewer_jt",
            password="password123",
        )
        cls.brand = BrandMateri.objects.create(name="Brand Visibility")
        cls.lokasi = Lokasi.objects.create(name="Lokasi Visibility")
        cls.led_type = LEDType.objects.create(name="LED Visibility")

    def create_jadwal_tayang(self):
        start_at = timezone.now()
        jadwal_tayang = JadwalTayang.objects.create(
            submitted_by=self.owner,
            brand_materi=self.brand,
            jenis_led=self.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=start_at + timedelta(hours=6),
            note_requester="Catatan visibility",
            pic_pemohon="Marketing",
        )
        jadwal_tayang.lokasi.set([self.lokasi])
        return jadwal_tayang

    def test_logged_in_user_can_view_other_users_jadwal_tayang_list_and_detail(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.viewer)

        list_response = self.client.get(reverse("jadwal_tayang_list"))
        detail_response = self.client.get(reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(list_response, "Brand Visibility")
        self.assertContains(list_response, "owner_jt")
        self.assertContains(detail_response, "Brand Visibility")
        self.assertContains(detail_response, "owner_jt")

    def test_dashboard_counts_visible_jadwal_tayang_for_logged_in_user(self):
        self.create_jadwal_tayang()
        self.client.force_login(self.viewer)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_jt"], 1)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class JadwalTayangListPhotoStatusTests(TestCase):
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
        cls.owner = get_user_model().objects.create_user(
            username="owner_photo_status",
            password="password123",
        )
        cls.viewer = get_user_model().objects.create_user(
            username="viewer_photo_status",
            password="password123",
        )
        cls.brand_no_photo = BrandMateri.objects.create(name="Brand No Photo")
        cls.brand_foto_tayang = BrandMateri.objects.create(name="Brand Foto Tayang")
        cls.brand_playlist = BrandMateri.objects.create(name="Brand Playlist")
        cls.brand_overdue = BrandMateri.objects.create(name="Brand Overdue")
        cls.brand_takeout = BrandMateri.objects.create(name="Brand Takeout")
        cls.lokasi = Lokasi.objects.create(name="Lokasi Photo Status")
        cls.led_type = LEDType.objects.create(name="LED Photo Status")

    def _upload_file(self, name):
        return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/jpeg")

    def create_jadwal_tayang(self, *, brand, start_at, takeout_at):
        jadwal_tayang = JadwalTayang.objects.create(
            submitted_by=self.owner,
            brand_materi=brand,
            jenis_led=self.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=takeout_at,
            note_requester="Catatan photo status",
            pic_pemohon="Marketing",
        )
        jadwal_tayang.lokasi.set([self.lokasi])
        return jadwal_tayang

    def test_list_uses_photo_based_status_labels(self):
        now = timezone.now()
        no_photo = self.create_jadwal_tayang(
            brand=self.brand_no_photo,
            start_at=now - timedelta(hours=1),
            takeout_at=now + timedelta(hours=3),
        )
        foto_tayang = self.create_jadwal_tayang(
            brand=self.brand_foto_tayang,
            start_at=now - timedelta(hours=2),
            takeout_at=now + timedelta(hours=2),
        )
        playlist_only = self.create_jadwal_tayang(
            brand=self.brand_playlist,
            start_at=now - timedelta(hours=2),
            takeout_at=now + timedelta(hours=2),
        )
        overdue = self.create_jadwal_tayang(
            brand=self.brand_overdue,
            start_at=now - timedelta(hours=5),
            takeout_at=now - timedelta(minutes=30),
        )
        takeout_done = self.create_jadwal_tayang(
            brand=self.brand_takeout,
            start_at=now - timedelta(hours=5),
            takeout_at=now - timedelta(hours=1),
        )

        JadwalTayangFotoTayang.objects.create(
            jadwal_tayang=foto_tayang,
            foto=self._upload_file("tayang.jpg"),
        )
        JadwalTayangBuktiPlaylist.objects.create(
            jadwal_tayang=playlist_only,
            foto_pagi=self._upload_file("playlist.jpg"),
        )
        JadwalTayangFotoTakeout.objects.create(
            jadwal_tayang=takeout_done,
            foto=self._upload_file("takeout.jpg"),
        )

        self.client.force_login(self.viewer)
        response = self.client.get(reverse("jadwal_tayang_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status Foto")
        self.assertContains(response, "Brand No Photo")
        self.assertContains(response, "Brand Foto Tayang")
        self.assertContains(response, "Brand Playlist")
        self.assertContains(response, "Brand Overdue")
        self.assertContains(response, "Brand Takeout")
        self.assertContains(response, '<span class="badge text-bg-secondary">Belum Upload Foto</span>', html=True)
        self.assertContains(response, '<span class="badge text-bg-info">Sudah Upload Foto Tayang</span>', html=True)
        self.assertContains(response, '<span class="badge text-bg-info">Sudah Upload Bukti Playlist</span>', html=True)
        self.assertContains(response, '<span class="badge text-bg-danger">Belum Takeout</span>', html=True)
        self.assertContains(response, '<span class="badge text-bg-success">Sudah Upload Foto Takeout</span>', html=True)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class JadwalTayangReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.viewer = get_user_model().objects.create_user(
            username="report_viewer",
            password="password123",
        )
        cls.owner = get_user_model().objects.create_user(
            username="report_owner",
            password="password123",
        )
        cls.brand_active_a = BrandMateri.objects.create(name="Brand Report Active A")
        cls.brand_active_b = BrandMateri.objects.create(name="Brand Report Active B")
        cls.brand_future = BrandMateri.objects.create(name="Brand Report Future")
        cls.brand_past = BrandMateri.objects.create(name="Brand Report Past")
        cls.lokasi_a = Lokasi.objects.create(name="Lokasi Report A")
        cls.lokasi_b = Lokasi.objects.create(name="Lokasi Report B")
        cls.led_type = LEDType.objects.create(name="LED Report")
        cls.dokumentator = Dokumentator.objects.create(name="Dokumentator Report")

    def create_jadwal_tayang(self, *, brand, lokasi, start_at, takeout_at, status="BELUM_TAYANG"):
        jadwal_tayang = JadwalTayang.objects.create(
            submitted_by=self.owner,
            brand_materi=brand,
            jenis_led=self.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=takeout_at,
            note_requester="Catatan report",
            pic_pemohon="Marketing Report",
            status=status,
        )
        jadwal_tayang.lokasi.set([lokasi])
        jadwal_tayang.pelaksana.set([self.dokumentator])
        return jadwal_tayang

    def test_report_shows_only_currently_active_jadwal_grouped_by_location(self):
        now = timezone.now()
        self.create_jadwal_tayang(
            brand=self.brand_active_a,
            lokasi=self.lokasi_a,
            start_at=now - timedelta(hours=2),
            takeout_at=now + timedelta(hours=2),
            status="BELUM_TAYANG",
        )
        self.create_jadwal_tayang(
            brand=self.brand_active_b,
            lokasi=self.lokasi_b,
            start_at=now - timedelta(minutes=30),
            takeout_at=now + timedelta(hours=4),
            status="SEDANG_TAYANG",
        )
        self.create_jadwal_tayang(
            brand=self.brand_future,
            lokasi=self.lokasi_a,
            start_at=now + timedelta(hours=1),
            takeout_at=now + timedelta(hours=6),
            status="SEDANG_TAYANG",
        )
        self.create_jadwal_tayang(
            brand=self.brand_past,
            lokasi=self.lokasi_b,
            start_at=now - timedelta(hours=8),
            takeout_at=now - timedelta(hours=1),
            status="SEDANG_TAYANG",
        )

        self.client.force_login(self.viewer)
        response = self.client.get(reverse("jadwal_tayang_report"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brand Report Active A")
        self.assertContains(response, "Brand Report Active B")
        self.assertNotContains(response, "Brand Report Future")
        self.assertNotContains(response, "Brand Report Past")
        self.assertContains(response, "Lokasi Report A")
        self.assertContains(response, "Lokasi Report B")
        self.assertEqual(response.context["active_count"], 2)
        self.assertEqual(
            [group["lokasi_name"] for group in response.context["report_groups"]],
            ["Lokasi Report A", "Lokasi Report B"],
        )

    def test_report_search_filters_active_results_only(self):
        now = timezone.now()
        self.create_jadwal_tayang(
            brand=self.brand_active_a,
            lokasi=self.lokasi_a,
            start_at=now - timedelta(hours=1),
            takeout_at=now + timedelta(hours=2),
        )
        self.create_jadwal_tayang(
            brand=self.brand_active_b,
            lokasi=self.lokasi_b,
            start_at=now - timedelta(hours=1),
            takeout_at=now + timedelta(hours=3),
        )

        self.client.force_login(self.viewer)
        response = self.client.get(reverse("jadwal_tayang_report"), {"q": "Lokasi Report B"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brand Report Active B")
        self.assertNotContains(response, "Brand Report Active A")
        self.assertEqual(response.context["active_count"], 1)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class ListSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="search_admin",
            email="search_admin@example.com",
            password="password123",
        )
        cls.user = get_user_model().objects.create_user(
            username="search_user",
            first_name="Sari",
            last_name="Lookup",
            email="sari.lookup@example.com",
            password="password123",
        )

        cls.brand_alpha = BrandMateri.objects.create(name="Brand Search Alpha")
        cls.brand_beta = BrandMateri.objects.create(name="Brand Search Beta")
        cls.lokasi_target = Lokasi.objects.create(name="Lokasi Search Target")
        cls.lokasi_other = Lokasi.objects.create(name="Lokasi Search Other")
        cls.led_type = LEDType.objects.create(name="LED Search")
        cls.requirement = Requirement.objects.create(name="Requirement Search")
        cls.view_photo = ViewPhoto.objects.create(name="View Search")
        cls.camera_type = cameratype.objects.create(name="Camera Search")
        cls.dokumentator = Dokumentator.objects.create(name="Dokumentator Search")
        cls.nama_perangkat_target = NamaPerangkat.objects.create(name="Panel Search Target")
        cls.nama_perangkat_other = NamaPerangkat.objects.create(name="Panel Search Other")

        cls.doc_request_target = DocumentationRequest.objects.create(
            submitted_by=cls.user,
            brand_materi=cls.brand_alpha,
            jenis_led=cls.led_type,
            tanggal=date.today(),
            note="Catatan alpha",
            pic_pemohon="PIC Alpha",
        )
        cls.doc_request_target.lokasi.set([cls.lokasi_target])
        cls.doc_request_target.requirements.set([cls.requirement])
        cls.doc_request_target.view_photo.set([cls.view_photo])
        cls.doc_request_target.jenis_kamera.set([cls.camera_type])

        cls.doc_request_other = DocumentationRequest.objects.create(
            submitted_by=cls.admin,
            brand_materi=cls.brand_beta,
            jenis_led=cls.led_type,
            tanggal=date.today(),
            note="Catatan beta",
            pic_pemohon="PIC Beta",
        )
        cls.doc_request_other.lokasi.set([cls.lokasi_other])
        cls.doc_request_other.requirements.set([cls.requirement])
        cls.doc_request_other.view_photo.set([cls.view_photo])
        cls.doc_request_other.jenis_kamera.set([cls.camera_type])

        cls.maint_request_target = MaintenanceRequest.objects.create(
            submitted_by=cls.user,
            nama_pemohon="Budi Search",
            departement="Engineering Search",
            tanggal_permintaan=date.today(),
            tanggal_deadline=date.today() + timedelta(days=1),
            deskripsi_pekerjaan="Perbaikan panel target",
        )
        cls.maint_request_target.nama_perangkat.set([cls.nama_perangkat_target])
        cls.maint_request_target.pelaksana.set([cls.dokumentator])

        cls.maint_request_other = MaintenanceRequest.objects.create(
            submitted_by=cls.admin,
            nama_pemohon="Andi Other",
            departement="Finance Other",
            tanggal_permintaan=date.today(),
            tanggal_deadline=date.today() + timedelta(days=2),
            deskripsi_pekerjaan="Perbaikan panel other",
        )
        cls.maint_request_other.nama_perangkat.set([cls.nama_perangkat_other])

        start_at = timezone.now()
        cls.jadwal_target = JadwalTayang.objects.create(
            submitted_by=cls.admin,
            brand_materi=cls.brand_alpha,
            jenis_led=cls.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=start_at + timedelta(minutes=30),
            note_requester="Request search target",
            pic_pemohon="PIC Search Jadwal",
        )
        cls.jadwal_target.lokasi.set([cls.lokasi_target])
        cls.jadwal_target.pelaksana.set([cls.dokumentator])

        cls.jadwal_other = JadwalTayang.objects.create(
            submitted_by=cls.user,
            brand_materi=cls.brand_beta,
            jenis_led=cls.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=start_at + timedelta(days=2),
            note_requester="Request other jadwal",
            pic_pemohon="PIC Other Jadwal",
        )
        cls.jadwal_other.lokasi.set([cls.lokasi_other])

        EditHistory.objects.create(
            user=cls.admin,
            request_type=EditHistory.RequestType.DOC_REQUEST,
            action="UPDATE",
            doc_request_id=cls.doc_request_target.pk,
            doc_request_label="Label Search History",
            field_name="PIC Search Field",
            old_value="Sebelum search",
            new_value="Sesudah search",
        )
        EditHistory.objects.create(
            user=cls.user,
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            action="CREATE",
            doc_request_id=cls.jadwal_other.pk,
            doc_request_label="Label Other History",
            field_name="Notes Other Field",
            old_value="",
            new_value="Other value",
        )

        cls.warning_rule = TakeoutAlertRule.objects.create(
            name="Search Warning Rule",
            trigger_direction=TakeoutAlertRule.TriggerDirection.BEFORE,
            offset_unit=TakeoutAlertRule.OffsetUnit.HOUR,
            offset_value=6,
            urgency=TakeoutAlertRule.Urgency.WARNING,
            is_active=True,
        )
        cls.urgent_rule = TakeoutAlertRule.objects.create(
            name="Search Urgent Rule",
            trigger_direction=TakeoutAlertRule.TriggerDirection.BEFORE,
            offset_unit=TakeoutAlertRule.OffsetUnit.HOUR,
            offset_value=1,
            urgency=TakeoutAlertRule.Urgency.URGENT,
            is_active=True,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_doc_request_list_search_filters_results(self):
        response = self.client.get(reverse("doc_request_list"), {"q": "Alpha"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brand Search Alpha")
        self.assertNotContains(response, "Brand Search Beta")

    def test_maintenance_request_list_search_filters_results(self):
        response = self.client.get(reverse("maint_request_list"), {"q": "Engineering Search"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Engineering Search")
        self.assertNotContains(response, "Finance Other")

    def test_jadwal_tayang_list_search_filters_results(self):
        response = self.client.get(reverse("jadwal_tayang_list"), {"q": "Lokasi Search Target"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lokasi Search Target")
        self.assertNotContains(response, "Lokasi Search Other")

    def test_master_data_list_search_filters_results(self):
        response = self.client.get(reverse("master_data_list", args=["lokasi"]), {"q": "Target"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lokasi Search Target")
        self.assertNotContains(response, "Lokasi Search Other")

    def test_user_list_search_filters_results(self):
        response = self.client.get(reverse("user_list"), {"q": "sari.lookup"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sari.lookup@example.com")
        self.assertQuerySetEqual(
            response.context["users"].values_list("username", flat=True),
            ["search_user"],
            transform=lambda value: value,
        )

    def test_edit_history_list_search_filters_results(self):
        response = self.client.get(reverse("edit_history_list"), {"q": "PIC Search Field"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PIC Search Field")
        self.assertNotContains(response, "Notes Other Field")

    def test_notification_list_search_filters_results(self):
        response = self.client.get(reverse("notification_list"), {"q": "Urgent Rule"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search Urgent Rule")
        self.assertNotContains(response, "Search Warning Rule")

    def test_takeout_alert_rule_list_search_filters_results(self):
        response = self.client.get(reverse("takeout_alert_rule_list"), {"q": "Warning Rule"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search Warning Rule")
        self.assertNotContains(response, "Search Urgent Rule")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class TakeoutNotificationTests(TestCase):
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
            username="admin_notification",
            email="admin_notification@example.com",
            password="password123",
        )
        cls.user = get_user_model().objects.create_user(
            username="staff_notification",
            password="password123",
        )
        cls.brand = BrandMateri.objects.create(name="Brand Notification")
        cls.lokasi = Lokasi.objects.create(name="Lokasi Notification")
        cls.led_type = LEDType.objects.create(name="LED Notification")
        TakeoutAlertRule.objects.all().delete()
        cls.warning_rule = TakeoutAlertRule.objects.create(
            name="H-1 Warning",
            trigger_direction=TakeoutAlertRule.TriggerDirection.BEFORE,
            offset_unit=TakeoutAlertRule.OffsetUnit.DAY,
            offset_value=1,
            urgency=TakeoutAlertRule.Urgency.WARNING,
            is_active=True,
        )
        cls.urgent_rule = TakeoutAlertRule.objects.create(
            name="Jam-6 Urgent",
            trigger_direction=TakeoutAlertRule.TriggerDirection.BEFORE,
            offset_unit=TakeoutAlertRule.OffsetUnit.HOUR,
            offset_value=6,
            urgency=TakeoutAlertRule.Urgency.URGENT,
            is_active=True,
        )

    def _upload_file(self, name):
        return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/jpeg")

    def create_jadwal_tayang(self, takeout_in_hours=4):
        start_at = timezone.now() - timedelta(hours=2)
        jadwal_tayang = JadwalTayang.objects.create(
            submitted_by=self.admin,
            brand_materi=self.brand,
            jenis_led=self.led_type,
            tanggal_tayang=start_at,
            tanggal_takeout=timezone.now() + timedelta(hours=takeout_in_hours),
            note_requester="Catatan requester",
            pic_pemohon="Marketing",
        )
        jadwal_tayang.lokasi.set([self.lokasi])
        return jadwal_tayang

    def test_notification_summary_returns_warning_and_urgent_notifications(self):
        jadwal_tayang = self.create_jadwal_tayang(takeout_in_hours=4)
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_summary"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["urgent_count"], 1)
        self.assertIn("H-1 Warning", payload["html"])
        self.assertIn("Jam-6 Urgent", payload["html"])
        self.assertEqual(
            payload["urgent_notifications"][0]["detail_url"],
            reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]),
        )

    def test_notification_list_available_for_logged_in_users(self):
        self.create_jadwal_tayang(takeout_in_hours=4)
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notifications")
        self.assertContains(response, "H-1 Warning")
        self.assertContains(response, "Jam-6 Urgent")

    def test_notifications_disappear_after_takeout_photo_exists(self):
        jadwal_tayang = self.create_jadwal_tayang(takeout_in_hours=4)
        JadwalTayangFotoTakeout.objects.create(
            jadwal_tayang=jadwal_tayang,
            foto=self._upload_file("takeout-finished.jpg"),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_summary"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["urgent_count"], 0)

    def test_after_takeout_rule_only_appears_after_trigger_time(self):
        TakeoutAlertRule.objects.all().delete()
        TakeoutAlertRule.objects.create(
            name="Jam+2 Warning",
            trigger_direction=TakeoutAlertRule.TriggerDirection.AFTER,
            offset_unit=TakeoutAlertRule.OffsetUnit.HOUR,
            offset_value=2,
            urgency=TakeoutAlertRule.Urgency.WARNING,
            is_active=True,
        )
        future_jadwal = self.create_jadwal_tayang(takeout_in_hours=1)
        past_jadwal = self.create_jadwal_tayang(takeout_in_hours=-3)
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_summary"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["urgent_count"], 0)
        self.assertIn("Jam+2 Warning", payload["html"])
        self.assertIn("Sudah lewat", payload["html"])
        self.assertIn(reverse("jadwal_tayang_detail", args=[past_jadwal.pk]), payload["html"])
        self.assertNotIn(reverse("jadwal_tayang_detail", args=[future_jadwal.pk]), payload["html"])

    def test_before_takeout_rule_stops_after_takeout_time(self):
        TakeoutAlertRule.objects.all().delete()
        TakeoutAlertRule.objects.create(
            name="Jam-1 Warning",
            trigger_direction=TakeoutAlertRule.TriggerDirection.BEFORE,
            offset_unit=TakeoutAlertRule.OffsetUnit.HOUR,
            offset_value=1,
            urgency=TakeoutAlertRule.Urgency.WARNING,
            is_active=True,
        )
        overdue_jadwal = self.create_jadwal_tayang(takeout_in_hours=-1)
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_summary"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 0)
        self.assertNotIn(reverse("jadwal_tayang_detail", args=[overdue_jadwal.pk]), payload["html"])

    def test_zero_hour_after_takeout_rule_can_trigger_immediately(self):
        TakeoutAlertRule.objects.all().delete()
        TakeoutAlertRule.objects.create(
            name="Jam+0 Warning",
            trigger_direction=TakeoutAlertRule.TriggerDirection.AFTER,
            offset_unit=TakeoutAlertRule.OffsetUnit.HOUR,
            offset_value=0,
            urgency=TakeoutAlertRule.Urgency.WARNING,
            is_active=True,
        )
        jadwal_tayang = self.create_jadwal_tayang(takeout_in_hours=0)
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_summary"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 1)
        self.assertIn("Jam+0 Warning", payload["html"])
        self.assertIn(reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]), payload["html"])

    def test_admin_can_create_takeout_alert_rule(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("takeout_alert_rule_create"),
            data={
                "name": "Jam+2 Warning",
                "trigger_direction": TakeoutAlertRule.TriggerDirection.AFTER,
                "offset_unit": TakeoutAlertRule.OffsetUnit.HOUR,
                "offset_value": 2,
                "urgency": TakeoutAlertRule.Urgency.WARNING,
                "is_active": "on",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        created_rule = TakeoutAlertRule.objects.get(name="Jam+2 Warning")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True})
        self.assertEqual(created_rule.lead_minutes, 120)
        self.assertEqual(created_rule.trigger_direction, TakeoutAlertRule.TriggerDirection.AFTER)
        self.assertEqual(created_rule.offset_display(), "Jam+2")

    def test_admin_can_create_zero_offset_takeout_alert_rule(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("takeout_alert_rule_create"),
            data={
                "name": "Jam+0 Warning",
                "trigger_direction": TakeoutAlertRule.TriggerDirection.AFTER,
                "offset_unit": TakeoutAlertRule.OffsetUnit.HOUR,
                "offset_value": 0,
                "urgency": TakeoutAlertRule.Urgency.WARNING,
                "is_active": "on",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        created_rule = TakeoutAlertRule.objects.get(name="Jam+0 Warning")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True})
        self.assertEqual(created_rule.lead_minutes, 0)
        self.assertEqual(created_rule.offset_display(), "Jam+0")
