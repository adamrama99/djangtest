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
    Requirement,
    TakeoutAlertRule,
    UserLoginRequirement,
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
        cls.requester_group, _ = Group.objects.get_or_create(name="requester")
        cls.staff_group, _ = Group.objects.get_or_create(name="staff")
        cls.executor_group, _ = Group.objects.get_or_create(name="executor")
        cls.requester = get_user_model().objects.create_user(
            username="requester_only",
            password="password123",
        )
        cls.requester.groups.add(cls.requester_group)
        cls.staff = get_user_model().objects.create_user(
            username="staff_only",
            password="password123",
        )
        cls.staff.groups.add(cls.staff_group)
        cls.executor = get_user_model().objects.create_user(
            username="executor_only",
            first_name="Executor",
            last_name="Only",
            password="password123",
        )
        cls.executor.groups.add(cls.executor_group)
        cls.brand = BrandMateri.objects.create(name="Brand Executor Access")
        cls.brand_other = BrandMateri.objects.create(name="Brand Hidden Executor")
        cls.lokasi = Lokasi.objects.create(name="Lokasi Executor Access")
        cls.lokasi_other = Lokasi.objects.create(name="Lokasi Hidden Executor")
        cls.led_type = LEDType.objects.create(name="LED Executor Access")
        cls.maint_led_type = LEDType.objects.create(name="Panel Executor Access")
        cls.maint_led_type_other = LEDType.objects.create(name="Panel Hidden Executor")
        cls.requirement = Requirement.objects.create(name="Requirement Executor Access")
        cls.view_photo = ViewPhoto.objects.create(name="View Executor Access")
        cls.camera_type = cameratype.objects.create(name="Camera Executor Access")
        cls.executor_dokumentator = Dokumentator.objects.create(name="Executor Only")
        cls.dokumentator_other = Dokumentator.objects.create(name="Dokumentator Lain")
        cls.dokumentator_extra = Dokumentator.objects.create(name="Dokumentator Extra")

        cls.doc_request = DocumentationRequest.objects.create(
            submitted_by=cls.requester,
            brand_materi=cls.brand,
            jenis_led=cls.led_type,
            tanggal=date.today(),
            note="Catatan untuk executor",
            pic_pemohon="PIC Executor",
        )
        cls.doc_request.lokasi.set([cls.lokasi])
        cls.doc_request.requirements.set([cls.requirement])
        cls.doc_request.view_photo.set([cls.view_photo])
        cls.doc_request.jenis_kamera.set([cls.camera_type])
        cls.doc_assignment = cls.doc_request.lokasi_assignments.get(lokasi=cls.lokasi)
        cls.doc_assignment.pelaksana.set([cls.executor_dokumentator])

        cls.doc_request_other = DocumentationRequest.objects.create(
            submitted_by=cls.requester,
            brand_materi=cls.brand_other,
            jenis_led=cls.led_type,
            tanggal=date.today(),
            note="Catatan tersembunyi",
            pic_pemohon="PIC Hidden",
        )
        cls.doc_request_other.lokasi.set([cls.lokasi_other])
        cls.doc_request_other.requirements.set([cls.requirement])
        cls.doc_request_other.view_photo.set([cls.view_photo])
        cls.doc_request_other.jenis_kamera.set([cls.camera_type])
        cls.doc_assignment_other = cls.doc_request_other.lokasi_assignments.get(lokasi=cls.lokasi_other)
        cls.doc_assignment_other.pelaksana.set([cls.dokumentator_other])

        cls.maint_request = MaintenanceRequest.objects.create(
            submitted_by=cls.requester,
            nama_pemohon="Pemohon Executor",
            departement="IT Support",
            tanggal_permintaan=date.today(),
            tanggal_deadline=date.today() + timedelta(days=1),
            deskripsi_pekerjaan="Maintenance untuk akses executor",
        )
        cls.maint_request.jenis_led.set([cls.maint_led_type])
        cls.maint_request.pelaksana.set([cls.executor_dokumentator])

        cls.maint_request_other = MaintenanceRequest.objects.create(
            submitted_by=cls.requester,
            nama_pemohon="Pemohon Hidden",
            departement="Finance Hidden",
            tanggal_permintaan=date.today(),
            tanggal_deadline=date.today() + timedelta(days=2),
            deskripsi_pekerjaan="Maintenance tersembunyi",
        )
        cls.maint_request_other.jenis_led.set([cls.maint_led_type_other])
        cls.maint_request_other.pelaksana.set([cls.dokumentator_other])

        cls.jadwal_tayang = JadwalTayang.objects.create(
            submitted_by=cls.requester,
            brand_materi=cls.brand,
            jenis_led=cls.led_type,
            tanggal_tayang=timezone.now(),
            tanggal_takeout=timezone.now() + timedelta(hours=4),
            note_requester="Jadwal untuk executor",
            pic_pemohon="PIC Jadwal Executor",
        )
        cls.jadwal_tayang.lokasi.set([cls.lokasi])

    def _upload_image(self, name="proof.gif"):
        tiny_gif = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x00"
            b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
            b"\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        return SimpleUploadedFile(name, tiny_gif, content_type="image/gif")

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

    def test_requester_and_staff_can_open_doc_and_maintenance_edit_pages(self):
        self.client.force_login(self.requester)
        requester_doc_response = self.client.get(reverse("doc_request_edit", args=[self.doc_request.pk]))
        requester_maint_response = self.client.get(reverse("maint_request_edit", args=[self.maint_request.pk]))

        self.client.force_login(self.staff)
        staff_doc_response = self.client.get(reverse("doc_request_edit", args=[self.doc_request.pk]))
        staff_maint_response = self.client.get(reverse("maint_request_edit", args=[self.maint_request.pk]))

        self.assertEqual(requester_doc_response.status_code, 200)
        self.assertEqual(requester_maint_response.status_code, 200)
        self.assertEqual(staff_doc_response.status_code, 200)
        self.assertEqual(staff_maint_response.status_code, 200)

    def test_executor_cannot_open_doc_and_maintenance_edit_pages(self):
        self.client.force_login(self.executor)

        doc_response = self.client.get(reverse("doc_request_edit", args=[self.doc_request.pk]))
        maint_response = self.client.get(reverse("maint_request_edit", args=[self.maint_request.pk]))

        self.assertEqual(doc_response.status_code, 403)
        self.assertEqual(maint_response.status_code, 403)

    def test_maintenance_create_page_uses_led_type_master_for_jenis_produk(self):
        self.client.force_login(self.requester)

        response = self.client.get(reverse("maint_request_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jenis Produk")
        self.assertContains(response, "LED Executor Access")
        self.assertContains(response, "Panel Executor Access")
        self.assertNotContains(response, "Nama Perangkat")

    def test_requester_and_staff_see_edit_shortcuts_but_executor_does_not(self):
        self.client.force_login(self.requester)
        requester_doc_list = self.client.get(reverse("doc_request_list"))
        requester_maint_list = self.client.get(reverse("maint_request_list"))

        self.client.force_login(self.staff)
        staff_doc_list = self.client.get(reverse("doc_request_list"))
        staff_maint_list = self.client.get(reverse("maint_request_list"))

        self.client.force_login(self.executor)
        executor_doc_list = self.client.get(reverse("doc_request_list"))
        executor_maint_list = self.client.get(reverse("maint_request_list"))

        self.assertContains(requester_doc_list, reverse("doc_request_edit", args=[self.doc_request.pk]))
        self.assertContains(requester_maint_list, reverse("maint_request_edit", args=[self.maint_request.pk]))
        self.assertContains(staff_doc_list, reverse("doc_request_edit", args=[self.doc_request.pk]))
        self.assertContains(staff_maint_list, reverse("maint_request_edit", args=[self.maint_request.pk]))
        self.assertNotContains(executor_doc_list, reverse("doc_request_edit", args=[self.doc_request.pk]))
        self.assertNotContains(executor_maint_list, reverse("maint_request_edit", args=[self.maint_request.pk]))

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

    def test_executor_only_sees_assigned_doc_and_maintenance_requests(self):
        self.client.force_login(self.executor)

        doc_response = self.client.get(reverse("doc_request_list"))
        maint_response = self.client.get(reverse("maint_request_list"))

        self.assertEqual(doc_response.status_code, 200)
        self.assertEqual(maint_response.status_code, 200)
        self.assertContains(doc_response, "Brand Executor Access")
        self.assertNotContains(doc_response, "Brand Hidden Executor")
        self.assertContains(maint_response, "Pemohon Executor")
        self.assertNotContains(maint_response, "Pemohon Hidden")

    def test_executor_can_view_only_assigned_detail_pages(self):
        self.client.force_login(self.executor)

        doc_response = self.client.get(reverse("doc_request_detail", args=[self.doc_request.pk]))
        maint_response = self.client.get(reverse("maint_request_detail", args=[self.maint_request.pk]))
        doc_forbidden_response = self.client.get(reverse("doc_request_detail", args=[self.doc_request_other.pk]))
        maint_forbidden_response = self.client.get(reverse("maint_request_detail", args=[self.maint_request_other.pk]))

        self.assertEqual(doc_response.status_code, 200)
        self.assertEqual(maint_response.status_code, 200)
        self.assertEqual(doc_forbidden_response.status_code, 403)
        self.assertEqual(maint_forbidden_response.status_code, 403)
        self.assertContains(doc_response, "PIC Executor")
        self.assertContains(maint_response, "IT Support")

    def test_requester_can_update_own_doc_and_maintenance_requests(self):
        self.client.force_login(self.requester)

        doc_response = self.client.post(
            reverse("doc_request_edit", args=[self.doc_request.pk]),
            data={
                "brand_materi": str(self.brand_other.id),
                "lokasi": [str(self.lokasi_other.id)],
                "jenis_led": str(self.led_type.id),
                "tanggal": date.today().isoformat(),
                "requirements": [str(self.requirement.id)],
                "view_photo": [str(self.view_photo.id)],
                "jenis_kamera": [str(self.camera_type.id)],
                "note": "Catatan requester update",
                "pic_pemohon": "PIC Updated",
            },
        )
        maint_response = self.client.post(
            reverse("maint_request_edit", args=[self.maint_request.pk]),
            data={
                "nama_pemohon": "Pemohon Updated",
                "departement": "IT Updated",
                "tanggal_permintaan": date.today().isoformat(),
                "tanggal_deadline": (date.today() + timedelta(days=3)).isoformat(),
                "brand_materi": str(self.brand_other.id),
                "lokasi": [str(self.lokasi_other.id)],
                "jenis_led": [str(self.maint_led_type_other.id)],
                "deskripsi_pekerjaan": "Maintenance updated requester",
            },
        )

        self.doc_request.refresh_from_db()
        self.maint_request.refresh_from_db()
        doc_history_fields = set(
            EditHistory.objects.filter(
                request_type=EditHistory.RequestType.DOC_REQUEST,
                doc_request_id=self.doc_request.pk,
                action="UPDATE",
            ).values_list("field_name", flat=True)
        )

        self.assertRedirects(doc_response, reverse("doc_request_detail", args=[self.doc_request.pk]))
        self.assertRedirects(maint_response, reverse("maint_request_detail", args=[self.maint_request.pk]))
        self.assertEqual(self.doc_request.brand_materi, self.brand_other)
        self.assertEqual(self.doc_request.lokasi_display(), self.lokasi_other.name)
        self.assertEqual(self.doc_request.note, "Catatan requester update")
        self.assertEqual(self.doc_request.pic_pemohon, "PIC Updated")
        self.assertTrue({"Brand / Materi", "Lokasi", "PIC Pemohon", "Note"}.issubset(doc_history_fields))
        self.assertEqual(self.maint_request.nama_pemohon, "Pemohon Updated")
        self.assertEqual(self.maint_request.departement, "IT Updated")
        self.assertEqual(self.maint_request.brand_materi, self.brand_other)
        self.assertEqual(self.maint_request.lokasi_display(), self.lokasi_other.name)
        self.assertQuerySetEqual(
            self.maint_request.jenis_led.order_by("name").values_list("name", flat=True),
            ["Panel Hidden Executor"],
            transform=lambda value: value,
        )

    def test_staff_can_update_doc_and_maintenance_requests(self):
        self.client.force_login(self.staff)

        doc_response = self.client.post(
            reverse("doc_request_edit", args=[self.doc_request.pk]),
            data={
                "brand_materi": str(self.brand.id),
                "lokasi": [str(self.lokasi.id)],
                "jenis_led": str(self.led_type.id),
                "tanggal": date.today().isoformat(),
                "requirements": [str(self.requirement.id)],
                "view_photo": [str(self.view_photo.id)],
                "jenis_kamera": [str(self.camera_type.id)],
                "note": "Catatan staff update",
                "pic_pemohon": "PIC Staff",
            },
        )
        maint_response = self.client.post(
            reverse("maint_request_edit", args=[self.maint_request.pk]),
            data={
                "nama_pemohon": "Pemohon Staff",
                "departement": "Departement Staff",
                "tanggal_permintaan": date.today().isoformat(),
                "tanggal_deadline": (date.today() + timedelta(days=4)).isoformat(),
                "brand_materi": str(self.brand.id),
                "lokasi": [str(self.lokasi.id)],
                "jenis_led": [str(self.maint_led_type.id)],
                "deskripsi_pekerjaan": "Maintenance updated staff",
            },
        )

        self.doc_request.refresh_from_db()
        self.maint_request.refresh_from_db()

        self.assertRedirects(doc_response, reverse("doc_request_detail", args=[self.doc_request.pk]))
        self.assertRedirects(maint_response, reverse("maint_request_detail", args=[self.maint_request.pk]))
        self.assertEqual(self.doc_request.note, "Catatan staff update")
        self.assertEqual(self.doc_request.pic_pemohon, "PIC Staff")
        self.assertEqual(self.maint_request.nama_pemohon, "Pemohon Staff")
        self.assertEqual(self.maint_request.departement, "Departement Staff")

    def test_staff_can_edit_pelaksana_in_doc_maintenance_and_jadwal(self):
        self.client.force_login(self.staff)

        doc_response = self.client.post(
            reverse("doc_request_update_lokasi_pelaksana", args=[self.doc_assignment.pk]),
            {"pelaksana[]": [self.executor_dokumentator.pk, self.dokumentator_extra.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        maint_response = self.client.post(
            reverse("maint_request_update_pelaksana", args=[self.maint_request.pk]),
            {"pelaksana[]": [self.dokumentator_extra.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        jadwal_response = self.client.post(
            reverse("jadwal_tayang_update_pelaksana", args=[self.jadwal_tayang.pk]),
            {"pelaksana[]": [self.dokumentator_extra.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.doc_assignment.refresh_from_db()
        self.maint_request.refresh_from_db()
        self.jadwal_tayang.refresh_from_db()

        self.assertEqual(doc_response.status_code, 200)
        self.assertEqual(maint_response.status_code, 200)
        self.assertEqual(jadwal_response.status_code, 200)
        self.assertQuerySetEqual(
            self.doc_assignment.pelaksana.order_by("name").values_list("name", flat=True),
            ["Dokumentator Extra", "Executor Only"],
            transform=lambda value: value,
        )
        self.assertQuerySetEqual(
            self.maint_request.pelaksana.order_by("name").values_list("name", flat=True),
            ["Dokumentator Extra"],
            transform=lambda value: value,
        )
        self.assertQuerySetEqual(
            self.jadwal_tayang.pelaksana.order_by("name").values_list("name", flat=True),
            ["Dokumentator Extra"],
            transform=lambda value: value,
        )

    def test_executor_cannot_edit_pelaksana_assignments(self):
        self.client.force_login(self.executor)

        doc_response = self.client.post(
            reverse("doc_request_update_lokasi_pelaksana", args=[self.doc_assignment.pk]),
            {"pelaksana[]": [self.dokumentator_extra.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        maint_response = self.client.post(
            reverse("maint_request_update_pelaksana", args=[self.maint_request.pk]),
            {"pelaksana[]": [self.dokumentator_extra.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        jadwal_response = self.client.post(
            reverse("jadwal_tayang_update_pelaksana", args=[self.jadwal_tayang.pk]),
            {"pelaksana[]": [self.dokumentator_extra.pk]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(doc_response.status_code, 403)
        self.assertEqual(maint_response.status_code, 403)
        self.assertEqual(jadwal_response.status_code, 403)

    def test_executor_can_upload_doc_request_proof_and_status_becomes_done(self):
        self.client.force_login(self.executor)

        response = self.client.post(
            reverse("doc_request_detail", args=[self.doc_request.pk]),
            {"foto_bukti_kerja": self._upload_image("doc-proof.gif")},
        )

        self.doc_request.refresh_from_db()

        self.assertRedirects(response, reverse("doc_request_detail", args=[self.doc_request.pk]))
        self.assertTrue(bool(self.doc_request.foto_bukti_kerja))
        self.assertEqual(self.doc_request.status, "DONE")

    def test_executor_can_upload_maintenance_proof_and_status_becomes_done(self):
        self.client.force_login(self.executor)

        response = self.client.post(
            reverse("maint_request_detail", args=[self.maint_request.pk]),
            {"foto_bukti_kerja": self._upload_image("maint-proof.gif")},
        )

        self.maint_request.refresh_from_db()

        self.assertRedirects(response, reverse("maint_request_detail", args=[self.maint_request.pk]))
        self.assertTrue(bool(self.maint_request.foto_bukti_kerja))
        self.assertEqual(self.maint_request.status, "DONE")

    def test_staff_can_upload_doc_and_maintenance_proof(self):
        self.client.force_login(self.staff)

        doc_response = self.client.post(
            reverse("doc_request_detail", args=[self.doc_request_other.pk]),
            {"foto_bukti_kerja": self._upload_image("doc-proof-staff.gif")},
        )
        maint_response = self.client.post(
            reverse("maint_request_detail", args=[self.maint_request_other.pk]),
            {"foto_bukti_kerja": self._upload_image("maint-proof-staff.gif")},
        )

        self.doc_request_other.refresh_from_db()
        self.maint_request_other.refresh_from_db()

        self.assertRedirects(doc_response, reverse("doc_request_detail", args=[self.doc_request_other.pk]))
        self.assertRedirects(maint_response, reverse("maint_request_detail", args=[self.maint_request_other.pk]))
        self.assertTrue(bool(self.doc_request_other.foto_bukti_kerja))
        self.assertTrue(bool(self.maint_request_other.foto_bukti_kerja))
        self.assertEqual(self.doc_request_other.status, "DONE")
        self.assertEqual(self.maint_request_other.status, "DONE")

    def test_executor_users_are_synced_into_dokumentator_dropdown(self):
        extra_executor = get_user_model().objects.create_user(
            username="new.exec",
            first_name="Budi",
            last_name="Executor",
            password="password123",
        )
        extra_executor.groups.add(self.executor_group)

        Dokumentator.objects.filter(name="Budi Executor").delete()

        self.client.force_login(self.staff)
        response = self.client.get(reverse("doc_request_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Budi Executor")
        self.assertTrue(Dokumentator.objects.filter(name="Budi Executor").exists())


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

    def test_create_view_saves_requester_reference_photo_and_link_for_each_created_location(self):
        self.client.force_login(self.admin)
        start_at = timezone.now()
        drive_link = "https://drive.google.com/file/d/requester-photo/view"

        response = self.client.post(
            reverse("jadwal_tayang_create"),
            data={
                "brand_materi": str(self.brand.id),
                "lokasi": [str(self.lokasi_a.id), str(self.lokasi_b.id)],
                "jenis_led": str(self.led_type.id),
                "tanggal_tayang": self._datetime_input(start_at),
                "tanggal_takeout": self._datetime_input(start_at + timedelta(hours=6)),
                "note_requester": "Catatan requester",
                "foto_referensi_requester": self._upload_file("requester-reference.jpg"),
                "link_foto_drive_requester": drive_link,
                "pic_pemohon": "Marketing",
            },
        )

        created_requests = JadwalTayang.objects.order_by("id")

        self.assertRedirects(response, reverse("jadwal_tayang_list"))
        self.assertEqual(created_requests.count(), 2)
        for request_obj in created_requests:
            self.assertTrue(bool(request_obj.foto_referensi_requester))
            self.assertEqual(request_obj.link_foto_drive_requester, drive_link)

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
        drive_link = "https://drive.google.com/file/d/updated-requester-photo/view"

        response = self.client.post(
            reverse("jadwal_tayang_edit", args=[jadwal_tayang.pk]),
            data={
                "brand_materi": str(self.brand_b.id),
                "lokasi": str(self.lokasi_b.id),
                "jenis_led": str(self.led_type_b.id),
                "tanggal_tayang": self._datetime_input(new_start_at),
                "tanggal_takeout": self._datetime_input(new_start_at + timedelta(hours=8)),
                "note_requester": "Catatan requester baru",
                "foto_referensi_requester": self._upload_file("edited-requester-reference.jpg"),
                "link_foto_drive_requester": drive_link,
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
        self.assertTrue(bool(jadwal_tayang.foto_referensi_requester))
        self.assertEqual(jadwal_tayang.link_foto_drive_requester, drive_link)
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
                "Foto Referensi Requester",
                "Link Foto Google Drive",
            },
        )

    def test_non_admin_cannot_access_edit_jadwal_tayang(self):
        jadwal_tayang = self.create_jadwal_tayang()
        self.client.force_login(self.staff)

        response = self.client.get(reverse("jadwal_tayang_edit", args=[jadwal_tayang.pk]))

        self.assertEqual(response.status_code, 403)

    def test_detail_page_shows_requester_reference_photo_and_drive_link(self):
        jadwal_tayang = self.create_jadwal_tayang()
        jadwal_tayang.foto_referensi_requester = self._upload_file("detail-requester-reference.jpg")
        jadwal_tayang.link_foto_drive_requester = "https://drive.google.com/file/d/detail-requester-reference/view"
        jadwal_tayang.save()
        self.client.force_login(self.admin)

        response = self.client.get(reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Foto Referensi Requester")
        self.assertContains(response, "Link Foto Google Drive")
        self.assertContains(response, jadwal_tayang.link_foto_drive_requester)
        self.assertContains(response, jadwal_tayang.foto_referensi_requester.url)


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
class UserLoginRequirementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="login_req_admin",
            email="login_req_admin@example.com",
            password="password123",
        )
        cls.needs_login = get_user_model().objects.create_user(
            username="needs_login",
            first_name="Need",
            last_name="Login",
            email="needs_login@example.com",
            password="password123",
        )
        cls.not_required = get_user_model().objects.create_user(
            username="service_account",
            email="service@example.com",
            password="password123",
        )
        UserLoginRequirement.objects.create(user=cls.not_required, requires_login=False)
        cls.already_logged_in = get_user_model().objects.create_user(
            username="already_logged_in",
            email="already@example.com",
            password="password123",
            last_login=timezone.now(),
        )
        cls.inactive_user = get_user_model().objects.create_user(
            username="inactive_never_login",
            email="inactive@example.com",
            password="password123",
            is_active=False,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_login_status_page_lists_required_users_with_counts(self):
        response = self.client.get(reverse("user_never_login_list"))

        self.assertEqual(response.status_code, 200)
        usernames = set(response.context["users"].values_list("username", flat=True))
        self.assertIn("needs_login", usernames)
        self.assertIn("already_logged_in", usernames)
        self.assertIn("inactive_never_login", usernames)
        self.assertNotIn("service_account", usernames)
        self.assertEqual(response.context["login_required_count"], len(usernames))
        self.assertEqual(
            response.context["never_login_count"],
            response.context["users"].filter(last_login__isnull=True).count(),
        )
        self.assertContains(response, "needs_login@example.com")
        self.assertContains(response, "already@example.com")
        self.assertContains(response, "inactive@example.com")
        self.assertContains(response, "Last Login")
        self.assertContains(
            response,
            f"{response.context['never_login_count']}/{response.context['login_required_count']} user belum login",
        )
        self.assertNotContains(response, "Date Joined")
        self.assertNotContains(response, "service@example.com")

    def test_user_form_can_mark_user_as_not_required_to_login(self):
        response = self.client.post(
            reverse("user_edit", args=[self.needs_login.pk]),
            data={
                "username": self.needs_login.username,
                "first_name": self.needs_login.first_name,
                "last_name": self.needs_login.last_name,
                "email": self.needs_login.email,
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("user_list"))
        self.assertFalse(self.needs_login.login_requirement.requires_login)

        never_login_response = self.client.get(reverse("user_never_login_list"))
        usernames = set(never_login_response.context["users"].values_list("username", flat=True))
        self.assertNotIn("needs_login", usernames)

    def test_user_list_can_toggle_login_requirement_inline(self):
        list_response = self.client.get(reverse("user_list"))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "user-login-required-toggle")
        self.assertContains(
            list_response,
            reverse("user_update_login_requirement", args=[self.needs_login.pk]),
        )

        response = self.client.post(
            reverse("user_update_login_requirement", args=[self.needs_login.pk]),
            {"requires_login": "false"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True, "requires_login": False})
        self.assertFalse(
            UserLoginRequirement.objects.get(user=self.needs_login).requires_login
        )

        response = self.client.post(
            reverse("user_update_login_requirement", args=[self.needs_login.pk]),
            {"requires_login": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True, "requires_login": True})
        self.assertTrue(
            UserLoginRequirement.objects.get(user=self.needs_login).requires_login
        )


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
        cls.maint_led_type_target = LEDType.objects.create(name="Panel Search Target")
        cls.maint_led_type_other = LEDType.objects.create(name="Panel Search Other")
        cls.requirement = Requirement.objects.create(name="Requirement Search")
        cls.view_photo = ViewPhoto.objects.create(name="View Search")
        cls.camera_type = cameratype.objects.create(name="Camera Search")
        cls.dokumentator = Dokumentator.objects.create(name="Dokumentator Search")

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
        cls.maint_request_target.jenis_led.set([cls.maint_led_type_target])
        cls.maint_request_target.pelaksana.set([cls.dokumentator])

        cls.maint_request_other = MaintenanceRequest.objects.create(
            submitted_by=cls.admin,
            nama_pemohon="Andi Other",
            departement="Finance Other",
            tanggal_permintaan=date.today(),
            tanggal_deadline=date.today() + timedelta(days=2),
            deskripsi_pekerjaan="Perbaikan panel other",
        )
        cls.maint_request_other.jenis_led.set([cls.maint_led_type_other])

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
