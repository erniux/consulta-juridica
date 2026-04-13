from datetime import date
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, TestCase

from apps.legal_documents.models import LegalDocument
from apps.legal_indexing.models import IngestionJob
from apps.legal_sources.models import Source

from .services.ingestion import _split_document, parse_document_into_fragments
from .services.jurisprudence_sync import (
    _parse_detail,
    _parse_search_results,
    search_jurisprudence_with_fallbacks,
    sync_jurisprudence_by_queries,
    sync_jurisprudence_for_prompt,
)
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


class JurisprudenceSyncTests(TestCase):
    SEARCH_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ObtenerResultadosResponse xmlns="http://sjf.scjn.gob.mx/">
      <ObtenerResultadosResult>
        <Resultados>
          <CamposComunesBE>
            <Id>2029196</Id>
            <Rubro>INCREMENTO DE LA INDEMNIZACION POR RIESGO DE TRABAJO.</Rubro>
            <Localizacion>Registro digital 2029196</Localizacion>
            <TipoTesis>Jurisprudencia</TipoTesis>
            <Tesis>2a./J. 123/2024</Tesis>
          </CamposComunesBE>
        </Resultados>
      </ObtenerResultadosResult>
    </ObtenerResultadosResponse>
  </soap:Body>
</soap:Envelope>"""

    DETAIL_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ObtenerDetalleResponse xmlns="http://tempuri.org/">
      <ObtenerDetalleResult>
        <Tesis>
          <Ius>2029196</Ius>
          <Tesis>2a./J. 123/2024</Tesis>
          <Rubro>INCREMENTO DE LA INDEMNIZACION POR RIESGO DE TRABAJO.</Rubro>
          <TipoTesis>Jurisprudencia</TipoTesis>
          <Instancia>Segunda Sala</Instancia>
          <Localizacion>Registro digital: 2029196</Localizacion>
          <FechaPublicacion>02/08/2024</FechaPublicacion>
          <Texto>Si un accidente de trabajo produce lesiones permanentes, la persona trabajadora puede reclamar indemnizacion adicional.</Texto>
          <Precedentes>Accidente de trabajo; incapacidad permanente parcial.</Precedentes>
          <Fuente>Semanario Judicial de la Federacion.</Fuente>
          <MateriasTesis>Laboral, Seguridad Social</MateriasTesis>
          <Referencia>Riesgo de trabajo</Referencia>
          <Tribunal>Segunda Sala</Tribunal>
          <RutaPdf>https://www.scjn.gob.mx/sites/default/files/comunicacion_digital/2024-08/tesis_publicacion_semanal_02082024.pdf</RutaPdf>
        </Tesis>
      </ObtenerDetalleResult>
    </ObtenerDetalleResponse>
  </soap:Body>
</soap:Envelope>"""

    def test_parse_search_results_reads_real_sjf_payload(self):
        results = _parse_search_results(self.SEARCH_XML)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ius, "2029196")
        self.assertEqual(results[0].tesis_clave, "2a./J. 123/2024")

    def test_parse_detail_reads_real_sjf_payload(self):
        detail = _parse_detail(self.DETAIL_XML)

        self.assertIsNotNone(detail)
        self.assertEqual(detail.ius, "2029196")
        self.assertEqual(detail.fecha_publicacion, date(2024, 8, 2))
        self.assertIn("indemnizacion adicional", detail.texto)

    @patch("apps.legal_indexing.services.jurisprudence_sync._post_soap_request")
    def test_sync_jurisprudence_by_queries_upserts_real_documents(self, mocked_post):
        mocked_post.side_effect = [self.SEARCH_XML, self.DETAIL_XML]

        documents = sync_jurisprudence_by_queries(
            ["riesgo de trabajo indemnizacion patron"],
            maximum_rows_per_query=5,
        )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document.digital_registry_number, "2029196")
        self.assertEqual(document.metadata_json["source_kind"], "sjf_webservice")
        self.assertEqual(document.metadata_json["search_expression"], "riesgo de trabajo indemnizacion patron")
        self.assertGreater(document.fragments.count(), 0)

    @patch("apps.legal_indexing.services.jurisprudence_sync.sync_jurisprudence_by_queries")
    def test_sync_jurisprudence_for_prompt_generates_queries_automatically(self, mocked_sync):
        mocked_sync.return_value = []

        sync_jurisprudence_for_prompt(
            "Obligaciones patronales por accidente de trabajo con perdida de unos dedos de la mano.",
            maximum_rows_per_query=7,
        )

        args, kwargs = mocked_sync.call_args
        self.assertGreater(len(args[0]), 1)
        self.assertEqual(kwargs["maximum_rows_per_query"], 7)
        self.assertTrue(any("riesgo de trabajo" in query for query in args[0]))

    @patch("apps.legal_indexing.services.jurisprudence_sync.get_jurisprudence_detail")
    @patch("apps.legal_indexing.services.jurisprudence_sync.search_jurisprudence_with_fallbacks")
    def test_sync_jurisprudence_by_queries_skips_failed_sjf_queries(
        self,
        mocked_search_with_fallbacks,
        mocked_detail,
    ):
        mocked_search_with_fallbacks.side_effect = [
            HTTPError(
                url="https://sjf.scjn.gob.mx/SJFSem/Servicios/wsResultados.asmx",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            ),
            (
                _parse_search_results(self.SEARCH_XML),
                "riesgo de trabajo indemnizacion patron",
            ),
        ]
        mocked_detail.return_value = _parse_detail(self.DETAIL_XML)

        documents = sync_jurisprudence_by_queries(
            [
                "consulta muy amplia que falla",
                "riesgo de trabajo indemnizacion patron",
            ],
            maximum_rows_per_query=5,
        )

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].digital_registry_number, "2029196")

    @patch("apps.legal_indexing.services.jurisprudence_sync.search_jurisprudence")
    def test_search_jurisprudence_with_fallbacks_uses_shorter_candidate_after_http_500(
        self,
        mocked_search,
    ):
        mocked_search.side_effect = [
            HTTPError(
                url="https://sjf.scjn.gob.mx/SJFSem/Servicios/wsResultados.asmx",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            ),
            [
                type(
                    "FakeResult",
                    (),
                    {
                        "ius": "2029196",
                        "rubro": "INCREMENTO DE LA INDEMNIZACION POR RIESGO DE TRABAJO.",
                        "localizacion": "Registro digital 2029196",
                        "tipo_tesis": "Jurisprudencia",
                        "tesis_clave": "2a./J. 123/2024",
                    },
                )()
            ],
        ]

        results, matched_expression = search_jurisprudence_with_fallbacks(
            "despido embarazo trabajadora",
            maximum_rows=5,
        )

        self.assertEqual(len(results), 1)
        self.assertNotEqual(matched_expression, "despido embarazo trabajadora")
        self.assertEqual(mocked_search.call_args_list[1].args[0], "despido embarazo")


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
