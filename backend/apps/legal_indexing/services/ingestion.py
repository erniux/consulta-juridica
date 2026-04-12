import re

from django.db import transaction
from django.utils import timezone

from common.text import normalize_text

from apps.legal_documents.models import LegalDocument

from ..models import DocumentFragment, IngestionJob
from .indexing import index_fragments


ARTICLE_HEADER_PATTERN = re.compile(
    r"^\s*(?P<header>Articulo\s+(?P<number>\d+[A-Za-z-]*(?:\s+[A-Za-z-]+)?)\.)\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
ARTICLE_TITLE_PATTERN = re.compile(
    r"^Articulo\s+(?P<number>\d+[A-Za-z-]*(?:\s+[A-Za-z-]+)?)$",
    re.IGNORECASE,
)


def _split_document(raw_text: str) -> list[tuple[str, str]]:
    normalized_source = (
        raw_text.replace("ArtÃƒÂ­culo", "Articulo")
        .replace("ArtÃ­culo", "Articulo")
        .replace("Artículo", "Articulo")
    )
    chunks = []
    current_title = None
    current_content_lines = []

    def flush_current_chunk():
        if not current_title:
            return
        content = "\n".join(line for line in current_content_lines if line).strip() or current_title
        chunks.append((current_title, content))

    for raw_line in normalized_source.splitlines():
        line = raw_line.strip()
        if not line:
            if current_title and current_content_lines and current_content_lines[-1] != "":
                current_content_lines.append("")
            continue

        article_header_match = ARTICLE_HEADER_PATTERN.match(line)
        if article_header_match:
            flush_current_chunk()
            current_title = article_header_match.group("header").rstrip(".")
            inline_content = article_header_match.group("rest").strip()
            current_content_lines = [inline_content] if inline_content else []
            continue

        if current_title:
            current_content_lines.append(line)

    if chunks or current_title:
        flush_current_chunk()
        return chunks

    paragraphs = [chunk.strip() for chunk in raw_text.split("\n\n") if chunk.strip()]
    return [(f"Fragmento {index}", paragraph) for index, paragraph in enumerate(paragraphs, start=1)]


@transaction.atomic
def parse_document_into_fragments(document: LegalDocument):
    DocumentFragment.objects.filter(legal_document=document).delete()
    created_fragments = []
    for index, (title, content) in enumerate(_split_document(document.raw_text), start=1):
        article_number = None
        article_match = ARTICLE_TITLE_PATTERN.match(title)
        if article_match:
            article_number = article_match.group("number")

        fragment = DocumentFragment.objects.create(
            legal_document=document,
            fragment_type=DocumentFragment.FragmentType.ARTICLE
            if article_number
            else DocumentFragment.FragmentType.SECTION,
            article_number=article_number or "",
            section_path=f"{document.short_name}/{index}",
            title=title,
            content=content,
            normalized_content=normalize_text(content),
            metadata_json={"seeded": document.metadata_json.get("seeded", False)},
            order_index=index,
        )
        created_fragments.append(fragment)

    index_fragments(created_fragments)
    return created_fragments


def run_ingestion_job(job: IngestionJob):
    job.status = IngestionJob.Status.PROCESSING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message", "updated_at"])

    try:
        official_source_slugs = (
            job.payload_json.get("official_source_slugs", []) if job.payload_json else []
        )
        if official_source_slugs:
            from .official_sync import sync_official_documents

            synced_documents = sync_official_documents(official_source_slugs)
            job.status = IngestionJob.Status.COMPLETED
            job.notes = (
                (job.notes or "") + f"\nSynced official documents: {len(synced_documents)}"
            ).strip()
            return job

        queryset = LegalDocument.objects.select_related("source")
        document_ids = job.payload_json.get("document_ids", []) if job.payload_json else []
        if document_ids:
            queryset = queryset.filter(id__in=document_ids)
        elif job.source_id:
            queryset = queryset.filter(source_id=job.source_id)

        processed = 0
        for document in queryset:
            parse_document_into_fragments(document)
            processed += 1

        job.status = IngestionJob.Status.COMPLETED
        job.notes = (job.notes or "") + f"\nProcessed documents: {processed}".strip()
    except Exception as exc:  # pragma: no cover - defensive runtime path.
        job.status = IngestionJob.Status.FAILED
        job.error_message = str(exc)
    finally:
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "notes",
                "error_message",
                "finished_at",
                "updated_at",
            ]
        )
    return job
