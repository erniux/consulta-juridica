from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.legal_sources.models import Source

from .models import LegalDocument


class LegalDocumentApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="documents-user",
            password="Docs12345!",
            role=user_model.Role.USER,
        )
        self.client.force_authenticate(self.user)
        source = Source.objects.create(
            name="Semanario Judicial de la Federacion",
            slug="sjf-test",
            type=Source.SourceType.JURISPRUDENCE,
            authority="SCJN",
            official_url="https://sjf2.scjn.gob.mx/",
            is_active=True,
        )
        self.document = LegalDocument.objects.create(
            source=source,
            title="Tesis aislada sobre riesgo de trabajo",
            short_name="Tesis RT",
            document_type=LegalDocument.DocumentType.THESIS,
            subject_area=LegalDocument.SubjectArea.OCCUPATIONAL_RISK,
            version_label="test-v1",
            digital_registry_number="2026001",
            official_url=source.official_url,
            raw_text="Rubro. Texto de prueba.",
        )

    def test_document_list_includes_digital_registry_number(self):
        response = self.client.get("/api/documents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["digital_registry_number"], "2026001")
        self.assertEqual(
            response.data["results"][0]["official_url"],
            "https://sjf2.scjn.gob.mx/detalle/tesis/2026001",
        )

    def test_document_list_can_search_by_digital_registry_number(self):
        response = self.client.get("/api/documents/", {"q": "2026001"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.document.id)
