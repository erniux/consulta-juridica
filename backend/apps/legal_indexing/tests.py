from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.legal_documents.models import LegalDocument
from apps.legal_indexing.models import IngestionJob
from apps.legal_sources.models import Source

from .services.ingestion import _split_document
from .services.official_sync import (
    OfficialPdfPayload,
    build_version_label,
    extract_last_reform_date,
    normalize_official_pdf_text,
    sync_official_documents,
)


class IngestionParsingTests(SimpleTestCase):
    def test_split_document_does_not_treat_inline_article_mentions_as_article_headers(self):
        raw_text = """
Rubro. Renuncia laboral con huella dactilar y firma autografa.

Criterio. Conforme al articulo 802 de la Ley Federal del Trabajo vigente hasta el 30 de noviembre de 2012, una renuncia exhibida en juicio conserva eficacia probatoria plena cuando se demuestra la autenticidad de la firma o de la huella dactilar.

Contexto. El criterio proviene de una contradiccion de tesis resuelta por la Segunda Sala.
""".strip()

        chunks = _split_document(raw_text)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0][0], "Fragmento 1")
        self.assertEqual(chunks[1][0], "Fragmento 2")
        self.assertIn("articulo 802", chunks[1][1].lower())

    def test_split_document_detects_real_article_headers_with_accents(self):
        raw_text = """
Artículo 1. La presente Ley es de observancia general.
Artículo 2. La seguridad social tiene por finalidad garantizar el derecho a la salud.
""".strip()

        chunks = _split_document(raw_text)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][0], "Artículo 1")
        self.assertEqual(chunks[1][0], "Artículo 2")


class OfficialSyncHelpersTests(SimpleTestCase):
    def test_extract_last_reform_date_from_official_pdf_text(self):
        raw_text = "LEY DEL SEGURO SOCIAL\nÚltima Reforma DOF 15-01-2026\nArtículo 1."

        reform_date = extract_last_reform_date(raw_text)

        self.assertEqual(reform_date, date(2026, 1, 15))

    def test_normalize_official_pdf_text_removes_headers_and_keeps_articles(self):
        raw_text = """
LEY DEL SEGURO SOCIAL
CÁMARA DE DIPUTADOS DEL H. CONGRESO DE LA UNIÓN
Secretaría General
Secretaría de Servicios Parlamentarios
Última Reforma DOF 15-01-2026
1 de 181
Artículo 1. La presente Ley es de observancia general.
""".strip()

        normalized = normalize_official_pdf_text(raw_text)

        self.assertNotIn("CÁMARA DE DIPUTADOS", normalized)
        self.assertIn("Artículo 1. La presente Ley es de observancia general.", normalized)

    def test_build_version_label_uses_last_reform_date_when_available(self):
        version_label = build_version_label(date(2026, 1, 15), "abc123")
        self.assertEqual(version_label, "vigente-2026-01-15")


class OfficialSyncTests(TestCase):
    @patch("apps.legal_indexing.services.official_sync.download_pdf_bytes")
    @patch("apps.legal_indexing.services.official_sync.extract_pdf_payload")
    def test_sync_official_documents_upserts_real_law_and_fragments(
        self,
        mocked_extract_payload,
        mocked_download,
    ):
        mocked_download.return_value = b"%PDF-test%"
        mocked_extract_payload.return_value = OfficialPdfPayload(
            raw_text="PDF raw text",
            cleaned_text=(
                "Artículo 1. La presente Ley es de observancia general.\n"
                "Artículo 2. La seguridad social tiene por finalidad garantizar el derecho a la salud."
            ),
            sha256="abcd1234" * 8,
            page_count=120,
            last_reform_date=date(2026, 1, 15),
        )

        documents = sync_official_documents(["lss"])

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document.short_name, "LSS")
        self.assertEqual(document.version_label, "vigente-2026-01-15")
        self.assertEqual(document.metadata_json["source_kind"], "official_pdf")
        self.assertEqual(document.fragments.count(), 2)
        self.assertTrue(
            Source.objects.filter(slug="lss", official_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf").exists()
        )
        self.assertTrue(
            LegalDocument.objects.filter(
                title="Ley del Seguro Social",
                version_label="vigente-2026-01-15",
                is_current=True,
            ).exists()
        )

    @patch("apps.legal_indexing.services.official_sync.sync_official_documents")
    def test_run_ingestion_job_supports_official_source_sync_payload(self, mocked_sync):
        mocked_sync.return_value = []
        job = IngestionJob.objects.create(
            job_type=IngestionJob.JobType.INGESTION,
            status=IngestionJob.Status.QUEUED,
            payload_json={"official_source_slugs": ["lft", "lss"]},
        )

        from .services.ingestion import run_ingestion_job

        run_ingestion_job(job)
        job.refresh_from_db()

        mocked_sync.assert_called_once_with(["lft", "lss"])
        self.assertEqual(job.status, IngestionJob.Status.COMPLETED)
