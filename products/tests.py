from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import DocumentationRequestForm
from .models import (
    BrandMateri,
    DocumentationRequest,
    DocumentationRequestLokasiAssignment,
    Dokumentator,
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
