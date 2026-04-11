from dataclasses import dataclass

from django.conf import settings

from common.text import cosine_similarity, deterministic_embedding, keyword_overlap_score

from apps.legal_documents.models import LegalDocument

from ..models import DocumentFragment


@dataclass
class RetrievalHit:
    fragment: DocumentFragment
    keyword_score: float
    semantic_score: float
    combined_score: float
    retrieval_type: str


def retrieve_fragments(query: str, limit: int | None = None, document_type: str | None = None):
    limit = limit or settings.DEFAULT_RETRIEVAL_LIMIT
    queryset = (
        DocumentFragment.objects.select_related("legal_document", "legal_document__source")
        .prefetch_related("embedding", "topic_relations__topic")
        .all()
    )

    if document_type:
        queryset = queryset.filter(legal_document__document_type=document_type)

    query_vector = deterministic_embedding(query, settings.VECTOR_DIMENSIONS)
    hits = []
    for fragment in queryset:
        keyword_score = keyword_overlap_score(query, fragment.content)
        embedding_vector = fragment.embedding.embedding if hasattr(fragment, "embedding") else None
        semantic_score = cosine_similarity(query_vector, embedding_vector)
        combined_score = round((keyword_score * 0.6) + (semantic_score * 0.4), 4)
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
