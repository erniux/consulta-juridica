import re

from django.db import transaction
from django.utils import timezone

from common.text import normalize_text

from apps.legal_documents.models import LegalDocument

from ..models import DocumentFragment, IngestionJob
from .indexing import index_fragments


ARTICLE_PATTERN = re.compile(
    r"(^\s*Art(?:í|i)culo\s+\d+[A-Za-z-]*\.?.*?)(?=^\s*Art(?:í|i)culo\s+\d+[A-Za-z-]*\.?|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)


def _split_document(raw_text: str) -> list[tuple[str, str]]:
    normalized_source = raw_text.replace("ArtÃ­culo", "Artículo")
    matches = ARTICLE_PATTERN.findall(normalized_source)
    if matches:
        chunks = []
        for match in matches:
            lines = [line.strip() for line in match.splitlines() if line.strip()]
            first_line = lines[0]
            article_header_match = re.match(
                r"^(Art(?:í|i)culo\s+\d+[A-Za-z-]*)(?:\.\s*(.*))?$",
                first_line,
                re.IGNORECASE,
            )
            if article_header_match:
                title = article_header_match.group(1).rstrip(".")
                inline_content = (article_header_match.group(2) or "").strip()
                content_lines = [inline_content] if inline_content else []
                content_lines.extend(lines[1:])
                content = "\n".join(content_lines).strip() or title
            else:
                title = first_line.rstrip(".")
                content = "\n".join(lines[1:]).strip() or title
            chunks.append((title, content))
        return chunks

    paragraphs = [chunk.strip() for chunk in raw_text.split("\n\n") if chunk.strip()]
    return [(f"Fragmento {index}", paragraph) for index, paragraph in enumerate(paragraphs, start=1)]


@transaction.atomic
def parse_document_into_fragments(document: LegalDocument):
    DocumentFragment.objects.filter(legal_document=document).delete()
    created_fragments = []
    for index, (title, content) in enumerate(_split_document(document.raw_text), start=1):
        article_number = None
        article_match = re.search(r"Art(?:í|i)culo\s+(\d+[A-Za-z-]*)", title, re.IGNORECASE)
        if article_match:
            article_number = article_match.group(1)

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
