import re
from dataclasses import dataclass

from django.conf import settings

from common.text import (
    cosine_similarity,
    deterministic_embedding,
    keyword_overlap_score,
    normalize_text,
)

from apps.legal_documents.models import LegalDocument

from ..models import DocumentFragment


ARTICLE_REFERENCE_PATTERN = re.compile(r"\barticulo\s+(\d+[a-z-]*)\b", re.IGNORECASE)
SOURCE_HINTS = {
    "lss": ["ley del seguro social", "lss", "seguro social"],
    "lft": ["ley federal del trabajo", "lft"],
}


@dataclass
class RetrievalHit:
    fragment: DocumentFragment
    keyword_score: float
    semantic_score: float
    combined_score: float
    retrieval_type: str


def _normalize_article_reference(value: str) -> str:
    return normalize_text(value).replace(" ", "").replace(".", "")


def _extract_target_article_numbers(query: str) -> set[str]:
    normalized_query = normalize_text(query)
    return {
        _normalize_article_reference(match.group(1))
        for match in ARTICLE_REFERENCE_PATTERN.finditer(normalized_query)
    }


def _extract_target_source_slugs(query: str) -> set[str]:
    normalized_query = normalize_text(query)
    selected = set()
    for slug, hints in SOURCE_HINTS.items():
        if any(hint in normalized_query for hint in hints):
            selected.add(slug)
    return selected


def _build_searchable_text(fragment: DocumentFragment) -> str:
    document = fragment.legal_document
    source = document.source
    return " ".join(
        value
        for value in [
            fragment.title,
            fragment.article_number,
            fragment.section_path,
            fragment.content,
            document.title,
            document.short_name,
            source.name,
            source.slug,
        ]
        if value
    )


def _source_specific_boost(fragment: DocumentFragment, target_source_slugs: set[str]) -> float:
    if not target_source_slugs:
        return 0.0
    return 0.85 if fragment.legal_document.source.slug in target_source_slugs else -0.25


def _article_specific_boost(fragment: DocumentFragment, target_article_numbers: set[str]) -> float:
    if not target_article_numbers:
        return 0.0
    fragment_article = _normalize_article_reference(fragment.article_number or "")
    if not fragment_article:
        return -0.05
    return 1.25 if fragment_article in target_article_numbers else -0.15


def retrieve_fragments(query: str, limit: int | None = None, document_type: str | None = None):
    limit = limit or settings.DEFAULT_RETRIEVAL_LIMIT
    queryset = (
        DocumentFragment.objects.select_related("legal_document", "legal_document__source")
        .prefetch_related("embedding", "topic_relations__topic")
        .all()
    )

    if document_type:
        queryset = queryset.filter(legal_document__document_type=document_type)

    target_source_slugs = _extract_target_source_slugs(query)
    if target_source_slugs:
        queryset = queryset.filter(legal_document__source__slug__in=target_source_slugs)

    target_article_numbers = _extract_target_article_numbers(query)
    query_vector = deterministic_embedding(query, settings.VECTOR_DIMENSIONS)
    hits = []
    for fragment in queryset:
        searchable_text = _build_searchable_text(fragment)
        keyword_score = keyword_overlap_score(query, searchable_text)
        embedding_vector = fragment.embedding.embedding if hasattr(fragment, "embedding") else None
        semantic_score = cosine_similarity(query_vector, embedding_vector)

        source_boost = _source_specific_boost(fragment, target_source_slugs)
        article_boost = _article_specific_boost(fragment, target_article_numbers)
        combined_score = round(
            (keyword_score * 0.55)
            + (semantic_score * 0.25)
            + source_boost
            + article_boost,
            4,
        )
        if combined_score <= 0:
            continue

        if keyword_score and semantic_score:
            retrieval_type = "hybrid"
        elif keyword_score:
            retrieval_type = "keyword"
        else:
            retrieval_type = "semantic"

        hits.append(
            RetrievalHit(
                fragment=fragment,
                keyword_score=keyword_score,
                semantic_score=semantic_score,
                combined_score=combined_score,
                retrieval_type=retrieval_type,
            )
        )

    hits.sort(key=lambda hit: hit.combined_score, reverse=True)
    return hits[:limit]


def document_type_for_search(scope: str):
    if scope == "jurisprudence":
        return LegalDocument.DocumentType.THESIS
    return None
