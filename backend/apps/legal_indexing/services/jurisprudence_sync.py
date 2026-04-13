from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.utils import timezone

from common.text import normalize_text, tokenize

from apps.legal_documents.models import LegalDocument
from apps.legal_sources.models import Source
from apps.llm_orchestrator.services.classifiers import (
    classify_matter,
    detect_topics,
    generate_jurisprudence_queries,
)


SCJN_BASE_URL = "https://bicentenario.scjn.gob.mx"
SCJN_SEARCH_URL = f"{SCJN_BASE_URL}/repositorio-scjn/api/reforma/busqueda"
SCJN_DETAIL_URLS = (
    f"{SCJN_BASE_URL}/api/v1/tesis/{{ius}}",
    f"{SCJN_BASE_URL}/repositorio-scjn/api/v1/tesis/{{ius}}",
)
SJF_PUBLIC_DETAIL_URL = "https://sjf2.scjn.gob.mx/detalle/tesis/{ius}"

logger = logging.getLogger(__name__)

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass(frozen=True)
class JurisprudenceSearchResult:
    ius: str
    rubro: str
    localizacion: str
    tipo_tesis: str
    tesis_clave: str
    raw_payload: dict


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
    nota_publica: str
    huella_digital: str
    anexos: str


def _normalize_whitespace(value: str | None) -> str:
    return " ".join((value or "").split())


def _parse_publication_date(payload: dict) -> date | None:
    nota_publica = _normalize_whitespace(str(payload.get("notaPublica", "")))
    normalized_note = normalize_text(nota_publica)
    tokens = normalized_note.split()
    for index, token in enumerate(tokens):
        if not token.isdigit():
            continue
        if index + 2 >= len(tokens):
            continue
        month = SPANISH_MONTHS.get(tokens[index + 2])
        if tokens[index + 1] != "de" or month is None:
            continue
        year_index = index + 3
        if year_index >= len(tokens) or tokens[year_index] != "de":
            continue
        if year_index + 1 >= len(tokens) or not tokens[year_index + 1].isdigit():
            continue
        try:
            return date(int(tokens[year_index + 1]), month, int(token))
        except ValueError:
            return None
    return None


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
        add_variant(" ".join(tokens[1:3]))

    for token in tokens[:4]:
        if len(token) >= 4:
            add_variant(token)

    return variants


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
) -> dict:
    headers = {
        "Accept": "application/json",
        "Referer": SCJN_BASE_URL,
        "User-Agent": "Mozilla/5.0 (compatible; consulta-juridica-bot/1.0; +https://github.com/)",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_search_payload(expression: str, maximum_rows: int) -> dict:
    return {
        "q": expression,
        "page": 1,
        "size": maximum_rows,
        "indice": "tesis",
        "filtros": {},
    }


def _parse_search_results(payload: dict | bytes | str) -> list[JurisprudenceSearchResult]:
    if isinstance(payload, bytes):
        payload = json.loads(payload.decode("utf-8"))
    elif isinstance(payload, str):
        payload = json.loads(payload)

    results = []
    for item in payload.get("resultados", []):
        ius = str(item.get("idTesis") or "").strip()
        if not ius:
            continue
        results.append(
            JurisprudenceSearchResult(
                ius=ius,
                rubro=_normalize_whitespace(str(item.get("rubro", ""))),
                localizacion=_normalize_whitespace(str(item.get("localizacion", ""))),
                tipo_tesis=_normalize_whitespace(str(item.get("tipoTesis", ""))),
                tesis_clave=_normalize_whitespace(str(item.get("tesis", ""))),
                raw_payload=item,
            )
        )
    return results


def _parse_detail(payload: dict | bytes | str) -> JurisprudenceDetail | None:
    if isinstance(payload, bytes):
        payload = json.loads(payload.decode("utf-8"))
    elif isinstance(payload, str):
        payload = json.loads(payload)

    ius = str(payload.get("idTesis") or "").strip()
    if not ius:
        return None

    materias = payload.get("materias") or []
    materias_text = ", ".join(
        _normalize_whitespace(str(materia)) for materia in materias if materia
    )

    nota_publica = _normalize_whitespace(str(payload.get("notaPublica", "")))
    referencia_parts = [
        nota_publica,
        _normalize_whitespace(str(payload.get("localizacion", ""))),
        _normalize_whitespace(str(payload.get("fuente", ""))),
    ]

    return JurisprudenceDetail(
        ius=ius,
        tesis_clave=_normalize_whitespace(str(payload.get("tesis", ""))) or f"Registro {ius}",
        rubro=_normalize_whitespace(str(payload.get("rubro", ""))),
        tipo_tesis=_normalize_whitespace(str(payload.get("tipoTesis", ""))),
        instancia=_normalize_whitespace(str(payload.get("instancia", ""))),
        localizacion=_normalize_whitespace(str(payload.get("localizacion", ""))),
        fecha_publicacion=_parse_publication_date(payload),
        texto=_normalize_whitespace(str(payload.get("texto", ""))),
        precedentes=_normalize_whitespace(str(payload.get("precedentes", ""))),
        fuente=_normalize_whitespace(str(payload.get("fuente", ""))),
        materias=materias_text,
        referencia=" | ".join(part for part in referencia_parts if part),
        tribunal=_normalize_whitespace(str(payload.get("organoJuris", ""))),
        ruta_pdf="",
        nota_publica=nota_publica,
        huella_digital=_normalize_whitespace(str(payload.get("huellaDigital", ""))),
        anexos=_normalize_whitespace(str(payload.get("anexos", ""))),
    )


def search_jurisprudence(expression: str, maximum_rows: int = 10) -> list[JurisprudenceSearchResult]:
    payload = _request_json(
        SCJN_SEARCH_URL,
        method="POST",
        payload=_build_search_payload(expression, maximum_rows),
    )
    return _parse_search_results(payload)


def search_jurisprudence_with_fallbacks(
    expression: str,
    maximum_rows: int = 10,
) -> tuple[list[JurisprudenceSearchResult], str]:
    last_exception = None

    for candidate in _fallback_search_expressions(expression):
        try:
            results = search_jurisprudence(candidate, maximum_rows=maximum_rows)
        except (HTTPError, URLError, ValueError) as exc:
            last_exception = exc
            logger.warning(
                "Jurisprudence search skipped for expression '%s' using candidate '%s': %s",
                expression,
                candidate,
                exc,
            )
            continue

        if results:
            if candidate != expression:
                logger.info(
                    "Jurisprudence search fallback succeeded for expression '%s' using '%s'",
                    expression,
                    candidate,
                )
            return results, candidate

    if last_exception is not None:
        raise last_exception
    return [], expression


def get_jurisprudence_detail(ius: str) -> JurisprudenceDetail | None:
    last_exception = None
    for template in SCJN_DETAIL_URLS:
        try:
            payload = _request_json(template.format(ius=ius))
            return _parse_detail(payload)
        except HTTPError as exc:
            last_exception = exc
            if exc.code == 404:
                continue
            raise
        except (URLError, ValueError) as exc:
            last_exception = exc
            continue

    if isinstance(last_exception, HTTPError):
        raise last_exception
    if isinstance(last_exception, URLError):
        raise last_exception
    return None


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
    if any(
        token in combined_text
        for token in ("riesgo de trabajo", "accidente de trabajo", "incapacidad", "indemnizacion")
    ):
        return LegalDocument.SubjectArea.OCCUPATIONAL_RISK
    if any(token in combined_text for token in ("seguro social", "imss", "pension")):
        return LegalDocument.SubjectArea.SOCIAL_SECURITY
    if any(
        token in combined_text
        for token in ("despido", "renuncia", "embarazo", "maternidad", "honorarios", "subordinacion", "hostigamiento")
    ):
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
        "official_url": SJF_PUBLIC_DETAIL_URL.format(ius=detail.ius),
        "raw_text": _build_raw_text(detail),
        "metadata_json": {
            "seeded": False,
            "source_kind": "scjn_repositorio_api",
            "instancia": detail.instancia,
            "tipo_tesis": detail.tipo_tesis,
            "localizacion": detail.localizacion,
            "materias": detail.materias,
            "referencia": detail.referencia,
            "tribunal": detail.tribunal,
            "ruta_pdf": detail.ruta_pdf,
            "fuente": detail.fuente,
            "search_expression": search_expression,
            "nota_publica": detail.nota_publica,
            "huella_digital": detail.huella_digital,
            "anexos": detail.anexos,
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
            "official_url": SCJN_BASE_URL,
            "description": "Tesis y precedentes recuperados del repositorio oficial SCJN/Bicentenario.",
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
        except (HTTPError, URLError, ValueError) as exc:
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
            except (HTTPError, URLError, ValueError) as exc:
                logger.warning(
                    "Jurisprudence detail skipped for ius '%s' and expression '%s': %s. Falling back to search payload.",
                    result.ius,
                    expression,
                    exc,
                )
                detail = None

            if not detail:
                detail = _parse_detail(result.raw_payload)
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


def sync_jurisprudence_for_prompt(
    prompt: str,
    *,
    maximum_rows_per_query: int = 10,
) -> list[LegalDocument]:
    matter = classify_matter(prompt)
    topics = detect_topics(prompt)
    queries = generate_jurisprudence_queries(prompt, matter, topics)
    return sync_jurisprudence_by_queries(
        queries,
        maximum_rows_per_query=maximum_rows_per_query,
    )
