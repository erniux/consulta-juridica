from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from urllib.request import Request, urlopen

from django.utils import timezone

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - dependency availability depends on environment setup.
    PdfReader = None

from apps.legal_documents.models import LegalDocument
from apps.legal_sources.models import Source


LAST_REFORM_PATTERN = re.compile(r"[ÚU]ltima Reforma DOF (\d{2}-\d{2}-\d{4})")

HEADER_PATTERNS = [
    re.compile(r"^C[ÁA]MARA DE DIPUTADOS.*$", re.IGNORECASE),
    re.compile(r"^Secretar[ií]a General$", re.IGNORECASE),
    re.compile(r"^Secretar[ií]a de Servicios Parlamentarios$", re.IGNORECASE),
    re.compile(r"^[ÚU]ltima Reforma DOF \d{2}-\d{2}-\d{4}$", re.IGNORECASE),
    re.compile(r"^\d+\s+de\s+\d+$", re.IGNORECASE),
]


@dataclass(frozen=True)
class OfficialDocumentDefinition:
    source_slug: str
    source_name: str
    authority: str
    source_type: str
    official_pdf_url: str
    description: str
    title: str
    short_name: str
    document_type: str
    subject_area: str
    publication_date: date
    effective_date: date
    jurisdiction: str = "federal"


@dataclass(frozen=True)
class OfficialPdfPayload:
    raw_text: str
    cleaned_text: str
    sha256: str
    page_count: int
    last_reform_date: date | None


OFFICIAL_DOCUMENTS = {
    "lft": OfficialDocumentDefinition(
        source_slug="lft",
        source_name="Ley Federal del Trabajo",
        authority="Camara de Diputados",
        source_type=Source.SourceType.LAW,
        official_pdf_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
        description="Texto vigente oficial de la Ley Federal del Trabajo.",
        title="Ley Federal del Trabajo",
        short_name="LFT",
        document_type=LegalDocument.DocumentType.LAW,
        subject_area=LegalDocument.SubjectArea.LABOR,
        publication_date=date(1970, 4, 1),
        effective_date=date(1970, 5, 1),
    ),
    "lss": OfficialDocumentDefinition(
        source_slug="lss",
        source_name="Ley del Seguro Social",
        authority="Camara de Diputados",
        source_type=Source.SourceType.LAW,
        official_pdf_url="https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf",
        description="Texto vigente oficial de la Ley del Seguro Social.",
        title="Ley del Seguro Social",
        short_name="LSS",
        document_type=LegalDocument.DocumentType.LAW,
        subject_area=LegalDocument.SubjectArea.SOCIAL_SECURITY,
        publication_date=date(1995, 12, 21),
        effective_date=date(1997, 7, 1),
    ),
}


def get_supported_official_slugs() -> list[str]:
    return sorted(OFFICIAL_DOCUMENTS.keys())


def download_pdf_bytes(url: str, timeout_seconds: int = 60) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "consulta-juridica-bot/1.0 (+https://github.com/)",
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def extract_pdf_payload(pdf_bytes: bytes) -> OfficialPdfPayload:
    if PdfReader is None:
        raise RuntimeError(
            "pypdf is required to sync official PDF documents. Install dependencies again."
        )
    reader = PdfReader(BytesIO(pdf_bytes))
    page_texts = [page.extract_text() or "" for page in reader.pages]
    raw_text = "\n".join(page_texts).strip()
    cleaned_text = normalize_official_pdf_text(raw_text)
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    return OfficialPdfPayload(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        sha256=sha256,
        page_count=len(reader.pages),
        last_reform_date=extract_last_reform_date(raw_text),
    )


def normalize_official_pdf_text(raw_text: str) -> str:
    normalized = raw_text.replace("ArtÃ­culo", "Artículo")
    cleaned_lines = []
    for raw_line in normalized.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            cleaned_lines.append("")
            continue
        if any(pattern.match(line) for pattern in HEADER_PATTERNS):
            continue
        cleaned_lines.append(line)

    collapsed = "\n".join(cleaned_lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    return collapsed.strip()


def extract_last_reform_date(raw_text: str) -> date | None:
    match = LAST_REFORM_PATTERN.search(raw_text)
    if not match:
        return None
    day, month, year = match.group(1).split("-")
    return date(int(year), int(month), int(day))


def build_version_label(last_reform_date: date | None, sha256: str) -> str:
    if last_reform_date:
        return f"vigente-{last_reform_date.isoformat()}"
    return f"sha-{sha256[:12]}"


def upsert_official_document(definition: OfficialDocumentDefinition) -> LegalDocument:
    from .ingestion import parse_document_into_fragments

    source, _ = Source.objects.update_or_create(
        slug=definition.source_slug,
        defaults={
            "name": definition.source_name,
            "type": definition.source_type,
            "authority": definition.authority,
            "official_url": definition.official_pdf_url,
            "description": definition.description,
            "is_active": True,
        },
    )

    pdf_bytes = download_pdf_bytes(definition.official_pdf_url)
    payload = extract_pdf_payload(pdf_bytes)
    version_label = build_version_label(payload.last_reform_date, payload.sha256)

    LegalDocument.objects.filter(
        source=source,
        title=definition.title,
        is_current=True,
    ).exclude(version_label=version_label).update(is_current=False)

    document, _ = LegalDocument.objects.update_or_create(
        source=source,
        title=definition.title,
        version_label=version_label,
        defaults={
            "short_name": definition.short_name,
            "document_type": definition.document_type,
            "jurisdiction": definition.jurisdiction,
            "subject_area": definition.subject_area,
            "publication_date": definition.publication_date,
            "effective_date": definition.effective_date,
            "last_reform_date": payload.last_reform_date,
            "official_url": definition.official_pdf_url,
            "raw_text": payload.cleaned_text,
            "metadata_json": {
                "seeded": False,
                "source_kind": "official_pdf",
                "download_url": definition.official_pdf_url,
                "page_count": payload.page_count,
                "content_sha256": payload.sha256,
                "fetched_at": timezone.now().isoformat(),
            },
            "is_current": True,
        },
    )
    parse_document_into_fragments(document)
    return document


def sync_official_documents(slugs: list[str] | None = None) -> list[LegalDocument]:
    selected_slugs = slugs or get_supported_official_slugs()
    invalid_slugs = sorted(set(selected_slugs) - set(OFFICIAL_DOCUMENTS))
    if invalid_slugs:
        supported = ", ".join(get_supported_official_slugs())
        raise ValueError(
            f"Unsupported official document slugs: {', '.join(invalid_slugs)}. "
            f"Supported values: {supported}."
        )

    synced_documents = []
    for slug in selected_slugs:
        synced_documents.append(upsert_official_document(OFFICIAL_DOCUMENTS[slug]))
    return synced_documents
