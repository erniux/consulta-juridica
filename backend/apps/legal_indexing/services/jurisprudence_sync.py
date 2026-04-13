from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from django.utils import timezone

from common.text import normalize_text, tokenize

from apps.legal_documents.models import LegalDocument
from apps.legal_sources.models import Source
from apps.llm_orchestrator.services.classifiers import (
    classify_matter,
    detect_topics,
    generate_jurisprudence_queries,
)


RESULTS_SERVICE_URL = "https://sjf.scjn.gob.mx/SJFSem/Servicios/wsResultados.asmx"
TESIS_SERVICE_URL = "https://sjf.scjn.gob.mx/sjfsem/Servicios/wsTesis.asmx"
SEARCH_PAGE_URL = "https://sjf.scjn.gob.mx/SJFSem/Paginas/ConsultaGlobal/BusquedaPrincipal.aspx"
SOAP_RESULTS_ACTION = "http://sjf.scjn.gob.mx/ObtenerResultados"
SOAP_DETAIL_ACTION = "http://tempuri.org/ObtenerDetalle"

SOAP_RESULTS_NS = {"soap": "http://schemas.xmlsoap.org/soap/envelope/", "svc": "http://sjf.scjn.gob.mx/"}
SOAP_DETAIL_NS = {"soap": "http://schemas.xmlsoap.org/soap/envelope/", "svc": "http://tempuri.org/"}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JurisprudenceSearchResult:
    ius: str
    rubro: str
    localizacion: str
    tipo_tesis: str
    tesis_clave: str


@dataclass(frozen=True)
class JurisprudenceDetail:
    ius: str
    tesis_clave: str
    rubro: str
    tipo_tesis: str
    instancia: str
    localizacion: str
    fecha_publicacion: date | None
    texto: str
    precedentes: str
    fuente: str
    materias: str
    referencia: str
    tribunal: str
    ruta_pdf: str


def _normalize_whitespace(value: str | None) -> str:
    return " ".join((value or "").split())


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _find_child(element: ET.Element | None, tag: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element:
        if _local_name(child.tag) == tag:
            return child
    return None


def _text(element: ET.Element | None, tag: str) -> str:
    child = _find_child(element, tag)
    return _normalize_whitespace(child.text if child is not None else "")


def _parse_date(value: str) -> date | None:
    cleaned = _normalize_whitespace(value).replace("-", "/")
    if not cleaned:
        return None
    parts = cleaned.split("/")
    if len(parts) != 3:
        return None
    day, month, year = parts
    if not (day.isdigit() and month.isdigit() and year.isdigit()):
        return None
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _build_search_envelope(expression: str, maximum_rows: int) -> str:
    escaped_expression = _escape_xml(expression)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ObtenerResultados xmlns="http://sjf.scjn.gob.mx/">
      <Url>{SEARCH_PAGE_URL}</Url>
      <FormMaster>
        <SoloIds>0</SoloIds>
        <TesisIDs></TesisIDs>
        <Expresion>{escaped_expression}</Expresion>
        <FTExpresion></FTExpresion>
        <Dominio></Dominio>
        <TATJ>0</TATJ>
        <OrdenadoPor>0</OrdenadoPor>
        <IDPonente>0</IDPonente>
        <IDAsunto>0</IDAsunto>
        <IDTipoTesis>0</IDTipoTesis>
        <IDCircuito>0</IDCircuito>
        <startRowIndex>0</startRowIndex>
        <maximumRows>{maximum_rows}</maximumRows>
        <Desde>1</Desde>
        <Hasta>{maximum_rows}</Hasta>
        <index>0</index>
        <IDTipoAcuerdo>0</IDTipoAcuerdo>
        <IDInstancia>0</IDInstancia>
        <Sesion></Sesion>
        <Octava>0</Octava>
        <IDParte>0</IDParte>
        <TotalElementos>0</TotalElementos>
        <IDTipoPonente>0</IDTipoPonente>
        <IDTribunalColegiado>0</IDTribunalColegiado>
        <IDTipoVoto>0</IDTipoVoto>
        <Tablero></Tablero>
        <TableroDGI></TableroDGI>
        <TableroCIDH></TableroCIDH>
        <TableroPO></TableroPO>
        <TableroEV></TableroEV>
        <Epoca>0</Epoca>
        <Anio>0</Anio>
        <Mes>0</Mes>
        <Semanas></Semanas>
        <Clase>Tesis</Clase>
        <CadenaEpoca></CadenaEpoca>
        <CadenaApendice></CadenaApendice>
        <IdTema>0</IdTema>
        <IdRaiz>0</IdRaiz>
        <Sinonimos></Sinonimos>
        <IdCto>0</IdCto>
        <IdEpoca>0</IdEpoca>
        <IdTcc>0</IdTcc>
        <IdMateria>0</IdMateria>
        <Indice></Indice>
        <DescTCC></DescTCC>
        <IdAbc></IdAbc>
        <IdProg>0</IdProg>
        <IdSesion></IdSesion>
        <TablaTema></TablaTema>
        <SeBuscaPorTema>0</SeBuscaPorTema>
      </FormMaster>
    </ObtenerResultados>
  </soap:Body>
</soap:Envelope>"""


def _build_detail_envelope(ius: str) -> str:
    escaped_ius = _escape_xml(ius)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ObtenerDetalle xmlns="http://tempuri.org/">
      <Url>{SEARCH_PAGE_URL}</Url>
      <IdActual>{escaped_ius}</IdActual>
      <IdELementos>{escaped_ius}</IdELementos>
      <IdSesion></IdSesion>
      <NumeroElementos>1</NumeroElementos>
      <Pagina>1</Pagina>
      <Desmarcar>0</Desmarcar>
      <tesisDesmarcadas></tesisDesmarcadas>
    </ObtenerDetalle>
  </soap:Body>
</soap:Envelope>"""


def _fallback_search_expressions(expression: str) -> list[str]:
    variants = []

    def add_variant(value: str):
        cleaned = " ".join((value or "").split())
        if cleaned and cleaned not in variants:
            variants.append(cleaned)

    add_variant(expression)
    normalized = normalize_text(expression)
    add_variant(normalized)

    tokens = tokenize(expression)
    if not tokens:
        return variants

    add_variant(" ".join(tokens[:5]))
    add_variant(" ".join(tokens[:4]))
    add_variant(" ".join(tokens[:3]))
    add_variant(" ".join(tokens[:2]))

    if len(tokens) >= 2:
        add_variant(" ".join(tokens[-2:]))
    if len(tokens) >= 3:
        add_variant(" ".join(tokens[:2]))
        add_variant(" ".join(tokens[1:3]))

    for token in tokens[:4]:
        if len(token) >= 4:
            add_variant(token)

    return variants


def _post_soap_request(url: str, action: str, envelope: str) -> bytes:
    attempts = [
        {
            "label": "SOAP 1.1",
            "headers": {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": action,
                "Accept": "text/xml, application/soap+xml, */*;q=0.8",
                "Referer": SEARCH_PAGE_URL,
                "User-Agent": "Mozilla/5.0 (compatible; consulta-juridica-bot/1.0; +https://github.com/)",
            },
        },
        {
            "label": "SOAP 1.2",
            "headers": {
                "Content-Type": f'application/soap+xml; charset=utf-8; action="{action}"',
                "Accept": "application/soap+xml, text/xml, */*;q=0.8",
                "Referer": SEARCH_PAGE_URL,
                "User-Agent": "Mozilla/5.0 (compatible; consulta-juridica-bot/1.0; +https://github.com/)",
            },
        },
    ]

    last_exception = None
    body = envelope.encode("utf-8")
    for attempt in attempts:
        request = Request(
            url,
            data=body,
            headers=attempt["headers"],
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            last_exception = exc
            if exc.code != 500:
                raise
            logger.warning(
                "SOAP request failed with %s against %s: %s",
                attempt["label"],
                url,
                exc,
            )

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("SOAP request could not be executed.")


def _parse_search_results(xml_bytes: bytes) -> list[JurisprudenceSearchResult]:
    root = ET.fromstring(xml_bytes)
    results = []
    for item in root.iter():
        if _local_name(item.tag) != "CamposComunesBE":
            continue
        ius = _text(item, "Id")
        if not ius:
            continue
        results.append(
            JurisprudenceSearchResult(
                ius=ius,
                rubro=_text(item, "Rubro"),
                localizacion=_text(item, "Localizacion"),
                tipo_tesis=_text(item, "TipoTesis"),
                tesis_clave=_text(item, "Tesis"),
            )
        )
    return results


def _parse_detail(xml_bytes: bytes) -> JurisprudenceDetail | None:
    root = ET.fromstring(xml_bytes)
    tesis = next((item for item in root.iter() if _local_name(item.tag) == "Tesis"), None)
    if tesis is None:
        return None

    ius = _text(tesis, "Ius")
    if not ius:
        return None

    return JurisprudenceDetail(
        ius=ius,
        tesis_clave=_text(tesis, "Tesis") or f"Registro {ius}",
        rubro=_text(tesis, "Rubro"),
        tipo_tesis=_text(tesis, "TipoTesis"),
        instancia=_text(tesis, "Instancia"),
        localizacion=_text(tesis, "Localizacion"),
        fecha_publicacion=_parse_date(_text(tesis, "FechaPublicacion")),
        texto=_text(tesis, "Texto"),
        precedentes=_text(tesis, "Precedentes"),
        fuente=_text(tesis, "Fuente"),
        materias=_text(tesis, "MateriasTesis"),
        referencia=_text(tesis, "Referencia"),
        tribunal=_text(tesis, "Tribunal"),
        ruta_pdf=_text(tesis, "RutaPdf"),
    )


def search_jurisprudence(expression: str, maximum_rows: int = 10) -> list[JurisprudenceSearchResult]:
    envelope = _build_search_envelope(expression, maximum_rows)
    xml_bytes = _post_soap_request(RESULTS_SERVICE_URL, SOAP_RESULTS_ACTION, envelope)
    return _parse_search_results(xml_bytes)


def search_jurisprudence_with_fallbacks(
    expression: str,
    maximum_rows: int = 10,
) -> tuple[list[JurisprudenceSearchResult], str]:
    last_exception = None

    for candidate in _fallback_search_expressions(expression):
        try:
            results = search_jurisprudence(candidate, maximum_rows=maximum_rows)
            if candidate != expression:
                logger.info(
                    "Jurisprudence search fallback succeeded for expression '%s' using '%s'",
                    expression,
                    candidate,
                )
            return results, candidate
        except (HTTPError, URLError, ET.ParseError) as exc:
            last_exception = exc
            logger.warning(
                "Jurisprudence search skipped for expression '%s' using candidate '%s': %s",
                expression,
                candidate,
                exc,
            )

    if last_exception is not None:
        raise last_exception
    return [], expression


def get_jurisprudence_detail(ius: str) -> JurisprudenceDetail | None:
    envelope = _build_detail_envelope(ius)
    xml_bytes = _post_soap_request(TESIS_SERVICE_URL, SOAP_DETAIL_ACTION, envelope)
    return _parse_detail(xml_bytes)


def _infer_subject_area(detail: JurisprudenceDetail) -> str:
    combined_text = " ".join(
        [
            detail.rubro,
            detail.texto,
            detail.precedentes,
            detail.materias,
            detail.referencia,
        ]
    ).lower()
    if any(token in combined_text for token in ("riesgo de trabajo", "accidente de trabajo", "incapacidad", "indemnizacion")):
        return LegalDocument.SubjectArea.OCCUPATIONAL_RISK
    if any(token in combined_text for token in ("seguro social", "imss", "pension")):
        return LegalDocument.SubjectArea.SOCIAL_SECURITY
    if any(token in combined_text for token in ("despido", "renuncia", "embarazo", "maternidad", "honorarios", "subordinacion", "hostigamiento")):
        return LegalDocument.SubjectArea.LABOR
    return LegalDocument.SubjectArea.GENERAL


def _build_raw_text(detail: JurisprudenceDetail) -> str:
    sections = []
    if detail.rubro:
        sections.append(f"Rubro. {detail.rubro}")
    if detail.texto:
        sections.append(f"Texto. {detail.texto}")
    if detail.precedentes:
        sections.append(f"Precedentes. {detail.precedentes}")
    if detail.materias:
        sections.append(f"Materias. {detail.materias}")
    if detail.localizacion:
        sections.append(f"Localizacion. {detail.localizacion}")
    if detail.referencia:
        sections.append(f"Referencia. {detail.referencia}")
    return "\n\n".join(sections)


def _upsert_jurisprudence_detail(
    detail: JurisprudenceDetail,
    *,
    source: Source,
    search_expression: str,
) -> LegalDocument:
    from .ingestion import parse_document_into_fragments

    existing = LegalDocument.objects.filter(
        source=source,
        digital_registry_number=detail.ius,
    ).first()
    defaults = {
        "title": (detail.rubro or detail.tesis_clave or f"Registro {detail.ius}")[:255],
        "short_name": (detail.tesis_clave or f"Registro {detail.ius}")[:100],
        "document_type": LegalDocument.DocumentType.THESIS,
        "subject_area": _infer_subject_area(detail),
        "publication_date": detail.fecha_publicacion,
        "effective_date": detail.fecha_publicacion,
        "last_reform_date": detail.fecha_publicacion,
        "version_label": f"registro-{detail.ius}",
        "digital_registry_number": detail.ius,
        "official_url": f"https://sjf2.scjn.gob.mx/detalle/tesis/{detail.ius}",
        "raw_text": _build_raw_text(detail),
        "metadata_json": {
            "seeded": False,
            "source_kind": "sjf_webservice",
            "instancia": detail.instancia,
            "tipo_tesis": detail.tipo_tesis,
            "localizacion": detail.localizacion,
            "materias": detail.materias,
            "referencia": detail.referencia,
            "tribunal": detail.tribunal,
            "ruta_pdf": detail.ruta_pdf,
            "fuente": detail.fuente,
            "search_expression": search_expression,
            "fetched_at": timezone.now().isoformat(),
        },
        "is_current": True,
    }

    if existing:
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save()
        document = existing
    else:
        document = LegalDocument.objects.create(source=source, **defaults)

    parse_document_into_fragments(document)
    return document


def sync_jurisprudence_by_queries(
    expressions: Iterable[str],
    *,
    maximum_rows_per_query: int = 10,
) -> list[LegalDocument]:
    source, _ = Source.objects.update_or_create(
        slug="sjf",
        defaults={
            "name": "Semanario Judicial de la Federacion",
            "type": Source.SourceType.JURISPRUDENCE,
            "authority": "SCJN",
            "official_url": "https://sjf2.scjn.gob.mx/busqueda-principal-tesis",
            "description": "Tesis y precedentes recuperados del Semanario Judicial de la Federacion.",
            "is_active": True,
        },
    )

    seen_ius = set()
    synced_documents = []
    for expression in expressions:
        if not expression:
            continue
        try:
            search_results, matched_expression = search_jurisprudence_with_fallbacks(
                expression,
                maximum_rows=maximum_rows_per_query,
            )
        except (HTTPError, URLError, ET.ParseError) as exc:
            logger.warning(
                "Jurisprudence search skipped for expression '%s' after all fallbacks: %s",
                expression,
                exc,
            )
            continue
        for result in search_results:
            if result.ius in seen_ius:
                continue
            seen_ius.add(result.ius)
            try:
                detail = get_jurisprudence_detail(result.ius)
            except (HTTPError, URLError, ET.ParseError) as exc:
                logger.warning(
                    "Jurisprudence detail skipped for ius '%s' and expression '%s': %s",
                    result.ius,
                    expression,
                    exc,
                )
                continue
            if not detail:
                continue
            synced_documents.append(
                _upsert_jurisprudence_detail(
                    detail,
                    source=source,
                    search_expression=matched_expression,
                )
            )
    return synced_documents


def sync_jurisprudence_for_prompt(prompt: str, *, maximum_rows_per_query: int = 10) -> list[LegalDocument]:
    matter = classify_matter(prompt)
    topics = detect_topics(prompt)
    queries = generate_jurisprudence_queries(prompt, matter, topics)
    return sync_jurisprudence_by_queries(
        queries,
        maximum_rows_per_query=maximum_rows_per_query,
    )
