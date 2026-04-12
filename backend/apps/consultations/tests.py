from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.legal_documents.models import LegalDocument
from apps.legal_indexing.services.ingestion import parse_document_into_fragments
from apps.legal_sources.models import Source

from .models import Consultation
from .services.workflow import process_consultation


@override_settings(LLM_PROVIDER="mock", DEFAULT_RETRIEVAL_LIMIT=4)
class ConsultationWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="demo", password="Demo12345!")
        self.source = Source.objects.create(
            name="Ley Federal del Trabajo",
            slug="lft",
            type=Source.SourceType.LAW,
            authority="Camara de Diputados",
            official_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
            is_active=True,
        )
        self.document = LegalDocument.objects.create(
            source=self.source,
            title="Ley Federal del Trabajo",
            short_name="LFT",
            document_type=LegalDocument.DocumentType.LAW,
            subject_area=LegalDocument.SubjectArea.LABOR,
            version_label="vigente",
            official_url=self.source.official_url,
            raw_text=(
                "Articulo 473. Riesgos de trabajo son los accidentes y enfermedades a que "
                "estan expuestos los trabajadores en ejercicio o con motivo del trabajo.\n\n"
                "Articulo 474. Accidente de trabajo es toda lesion organica o perturbacion "
                "funcional producida repentinamente en ejercicio o con motivo del trabajo."
            ),
        )
        parse_document_into_fragments(self.document)
        self.jurisprudence_source = Source.objects.create(
            name="Semanario Judicial de la Federacion",
            slug="sjf",
            type=Source.SourceType.JURISPRUDENCE,
            authority="SCJN",
            official_url="https://sjf2.scjn.gob.mx/busqueda-principal-tesis",
            is_active=True,
        )
        self.jurisprudence_document = LegalDocument.objects.create(
            source=self.jurisprudence_source,
            title="Renuncia laboral con huella y firma: eficacia probatoria",
            short_name="2a./J. 6/2021",
            document_type=LegalDocument.DocumentType.THESIS,
            subject_area=LegalDocument.SubjectArea.LABOR,
            version_label="registro-2023053",
            digital_registry_number="2023053",
            official_url="https://sjf2.scjn.gob.mx/detalle/tesis/2023053",
            raw_text=(
                "Rubro. Renuncia laboral con huella dactilar y firma autografa.\n\n"
                "Criterio. Basta acreditar la veracidad de uno de esos elementos para dar "
                "eficacia probatoria a la renuncia en terminos del articulo 802 de la LFT."
            ),
        )
        parse_document_into_fragments(self.jurisprudence_document)

    def test_process_consultation_generates_citations(self):
        consultation = Consultation.objects.create(
            user=self.user,
            prompt="Tuve un accidente de trabajo y quiero saber mis derechos.",
        )

        process_consultation(consultation)
        consultation.refresh_from_db()

        self.assertEqual(consultation.status, Consultation.Status.COMPLETED)
        self.assertTrue(consultation.final_answer)
        self.assertGreater(consultation.citations.count(), 0)

    def test_process_consultation_includes_digital_registry_number_for_jurisprudence(self):
        consultation = Consultation.objects.create(
            user=self.user,
            prompt="Me hicieron firmar una renuncia despues de un accidente de trabajo.",
        )

        process_consultation(consultation)
        consultation.refresh_from_db()

        self.assertEqual(consultation.status, Consultation.Status.COMPLETED)
        self.assertIn("registro digital 2023053", consultation.final_answer)

    @patch("apps.consultations.services.workflow.generate_consultation_answer")
    def test_process_consultation_marks_failed_when_unexpected_error_happens(self, mocked_generate):
        mocked_generate.side_effect = RuntimeError("provider down")
        consultation = Consultation.objects.create(
            user=self.user,
            prompt="Necesito revisar un accidente de trabajo.",
        )

        process_consultation(consultation)
        consultation.refresh_from_db()

        self.assertEqual(consultation.status, Consultation.Status.FAILED)
        self.assertIn("provider down", consultation.error_message)


class ConsultationAccessTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner",
            password="Owner12345!",
            role=user_model.Role.USER,
        )
        self.other = user_model.objects.create_user(
            username="other",
            password="Other12345!",
            role=user_model.Role.USER,
        )
        self.owner_consultation = Consultation.objects.create(
            user=self.owner,
            prompt="Consulta del owner",
            status=Consultation.Status.COMPLETED,
        )
        self.other_consultation = Consultation.objects.create(
            user=self.other,
            prompt="Consulta de otro usuario",
            status=Consultation.Status.COMPLETED,
        )

    def test_regular_user_only_lists_own_consultations(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get("/api/consultations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.owner_consultation.id)

    def test_regular_user_cannot_access_other_consultation_detail(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(f"/api/consultations/{self.other_consultation.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_regular_user_can_delete_own_consultation(self):
        self.client.force_authenticate(self.owner)

        response = self.client.delete(f"/api/consultations/{self.owner_consultation.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Consultation.objects.filter(pk=self.owner_consultation.id).exists())

    def test_regular_user_cannot_delete_other_consultation(self):
        self.client.force_authenticate(self.owner)

        response = self.client.delete(f"/api/consultations/{self.other_consultation.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
