from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.legal_documents.models import LegalDocument
from apps.legal_indexing.models import IngestionJob
from apps.legal_sources.models import Source

from .services.ingestion import _split_document, parse_document_into_fragments
from .services.official_sync import (
    OfficialPdfPayload,
    build_version_label,
    extract_last_reform_date,
    normalize_official_pdf_text,
    sync_official_documents,
)
from .services.retrieval import retrieve_fragments


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

    def test_split_document_detects_real_article_headers(self):
        raw_text = """
Articulo 1. La presente Ley es de observancia general.
Articulo 2. La seguridad social tiene por finalidad garantizar el derecho a la salud.
""".strip()

        chunks = _split_document(raw_text)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][0], "Articulo 1")
        self.assertEqual(chunks[1][0], "Articulo 2")

    def test_split_document_ignores_lines_that_only_start_like_articles(self):
        raw_text = """
Articulo 15. Los patrones deben registrarse ante el Instituto.
articulo 15 A de esta Ley, y tendran hasta el 1 de septiembre de 2021 para regularizarse.
Articulo 16. Los patrones deben determinar las cuotas obrero patronales.
""".strip()

        chunks = _split_document(raw_text)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][0], "Articulo 15")
        self.assertIn("articulo 15 A de esta Ley", chunks[0][1])
        self.assertEqual(chunks[1][0], "Articulo 16")


class OfficialSyncHelpersTests(SimpleTestCase):
    def test_extract_last_reform_date_from_official_pdf_text(self):
        raw_text = "LEY DEL SEGURO SOCIAL\nUltima Reforma DOF 15-01-2026\nArticulo 1."

        reform_date = extract_last_reform_date(raw_text)

        self.assertEqual(reform_date, date(2026, 1, 15))

    def test_normalize_official_pdf_text_removes_headers_and_keeps_articles(self):
        raw_text = """
LEY DEL SEGURO SOCIAL
CAMARA DE DIPUTADOS DEL H. CONGRESO DE LA UNION
Secretaria General
Secretaria de Servicios Parlamentarios
Ultima Reforma DOF 15-01-2026
1 de 181
Articulo 1. La presente Ley es de observancia general.
""".strip()

        normalized = normalize_official_pdf_text(raw_text)

        self.assertNotIn("CAMARA DE DIPUTADOS", normalized)
        self.assertIn("Articulo 1. La presente Ley es de observancia general.", normalized)

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
                "Articulo 1. La presente Ley es de observancia general.\n"
                "Articulo 2. La seguridad social tiene por finalidad garantizar el derecho a la salud."
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
            Source.objects.filter(
                slug="lss",
                official_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf",
            ).exists()
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


class RetrievalRankingTests(TestCase):
    def setUp(self):
        self.lss_source = Source.objects.create(
            name="Ley del Seguro Social",
            slug="lss",
            type=Source.SourceType.LAW,
            authority="Camara de Diputados",
            official_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf",
            is_active=True,
        )
        self.lft_source = Source.objects.create(
            name="Ley Federal del Trabajo",
            slug="lft",
            type=Source.SourceType.LAW,
            authority="Camara de Diputados",
            official_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
            is_active=True,
        )
        self.lss_document = LegalDocument.objects.create(
            source=self.lss_source,
            title="Ley del Seguro Social",
            short_name="LSS",
            document_type=LegalDocument.DocumentType.LAW,
            subject_area=LegalDocument.SubjectArea.SOCIAL_SECURITY,
            version_label="vigente-2026-01-15",
            official_url=self.lss_source.official_url,
            raw_text=(
                "Articulo 15. Las personas empleadoras estan obligadas a registrarse e inscribir "
                "a sus trabajadores ante el Instituto, comunicar sus altas y bajas, modificaciones "
                "de salario y los demas datos en los plazos legales.\n\n"
                "Articulo 286 K. El buzon IMSS es el sistema de comunicacion electronica mediante el cual el Instituto realiza notificaciones, requerimientos y tramites digitales.\n\n"
                "Articulo 150. El Instituto podra realizar acciones complementarias de verificacion administrativa.\n\n"
                "Articulo 43. En caso de accidente de trabajo el patron debe dar aviso al Instituto.\n\n"
                "Articulo 58. El asegurado que sufra un riesgo de trabajo tiene derecho a prestaciones."
            ),
        )
        parse_document_into_fragments(self.lss_document)
        self.lft_document = LegalDocument.objects.create(
            source=self.lft_source,
            title="Ley Federal del Trabajo",
            short_name="LFT",
            document_type=LegalDocument.DocumentType.LAW,
            subject_area=LegalDocument.SubjectArea.LABOR,
            version_label="vigente-2026-01-15",
            official_url=self.lft_source.official_url,
            raw_text=(
                "Articulo 51. Son causas de rescision de la relacion de trabajo sin responsabilidad para el trabajador.\n\n"
                "Articulo 474. Accidente de trabajo es toda lesion organica producida repentinamente."
            ),
        )
        parse_document_into_fragments(self.lft_document)
        self.old_lss_demo_document = LegalDocument.objects.create(
            source=self.lss_source,
            title="Ley del Seguro Social",
            short_name="LSS",
            document_type=LegalDocument.DocumentType.LAW,
            subject_area=LegalDocument.SubjectArea.SOCIAL_SECURITY,
            version_label="demo-lss-v1",
            official_url=self.lss_source.official_url,
            raw_text="Articulo 58. El asegurado que sufra un riesgo de trabajo tiene derecho a prestaciones.",
            metadata_json={"seeded": True, "source_kind": "demo_seed"},
            is_current=False,
        )
        parse_document_into_fragments(self.old_lss_demo_document)

    def test_retrieve_fragments_prioritizes_exact_article_and_source_match(self):
        hits = retrieve_fragments(
            "Que dice el articulo 15 de la Ley del Seguro Social sobre obligaciones del patron?",
            limit=3,
        )

        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].fragment.legal_document.short_name, "LSS")
        self.assertEqual(hits[0].fragment.article_number, "15")
        self.assertTrue(all(hit.fragment.article_number == "15" for hit in hits))

    def test_retrieve_fragments_ignores_non_current_documents(self):
        hits = retrieve_fragments(
            "Que dice el articulo 58 de la Ley del Seguro Social?",
            limit=5,
        )

        self.assertTrue(all(hit.fragment.legal_document.is_current for hit in hits))

    def test_retrieve_fragments_prioritizes_buzon_imss_for_short_query(self):
        hits = retrieve_fragments(
            "Que es el buzon IMSS?",
            limit=3,
        )

        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].fragment.legal_document.short_name, "LSS")
        self.assertEqual(hits[0].fragment.article_number, "286 K")
