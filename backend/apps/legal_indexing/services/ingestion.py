import re

from django.db import transaction
from django.utils import timezone

from common.text import normalize_text

from apps.legal_documents.models import LegalDocument

from ..models import DocumentFragment, IngestionJob
from .indexing import index_fragments


ARTICLE_PATTERN = re.compile(
    r"(Articulo\s+\d+[A-Za-z-]*\.?.*?)(?=(?:\nArticulo\s+\d+[A-Za-z-]*\.?)|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def _split_document(raw_text: str) -> list[tuple[str, str]]:
    normalized_source = raw_text.replace("Artículo", "Articulo")
    matches = ARTICLE_PATTERN.findall(normalized_source)
    if matches:
        chunks = []
        for match in matches:
            lines = [line.strip() for line in match.splitlines() if line.strip()]
            title = lines[0].rstrip(".")
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
        article_match = re.search(r"Articulo\s+(\d+[A-Za-z-]*)", title, re.IGNORECASE)
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
