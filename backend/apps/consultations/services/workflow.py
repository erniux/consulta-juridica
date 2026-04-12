from django.conf import settings
from django.db import transaction

from common.text import normalize_text

from apps.citations.models import ConsultationCitation
from apps.legal_documents.models import LegalDocument
from apps.legal_indexing.models import DocumentFragment
from apps.legal_indexing.services.retrieval import retrieve_fragments
from apps.llm_orchestrator.services.classifiers import classify_matter, detect_topics, expand_query
from apps.llm_orchestrator.services.orchestrator import generate_consultation_answer

from ..models import Consultation, ConsultationRetrieval


JURISPRUDENCE_DOCUMENT_TYPES = {
    LegalDocument.DocumentType.THESIS,
    LegalDocument.DocumentType.PRECEDENT,
}
JURISPRUDENCE_ELIGIBLE_MATTERS = {
    "occupational_risk",
    "social_security",
    "labor_individual",
}
JURISPRUDENCE_ELIGIBLE_TOPICS = {
    "riesgo-de-trabajo",
    "seguridad-social",
    "renuncia-forzada",
    "despido",
    "indemnizacion-riesgo-trabajo",
}


def _merge_hits(hit_groups):
    merged = {}
    for hits in hit_groups:
        for hit in hits:
            current = merged.get(hit.fragment.id)
            if current is None or hit.combined_score > current.combined_score:
                merged[hit.fragment.id] = hit
    return sorted(merged.values(), key=lambda item: item.combined_score, reverse=True)


def _is_jurisprudence_hit(hit) -> bool:
    return hit.fragment.legal_document.document_type in JURISPRUDENCE_DOCUMENT_TYPES


def _should_include_jurisprudence(matter: str, topics: list[str]) -> bool:
    return matter in JURISPRUDENCE_ELIGIBLE_MATTERS or bool(
        set(topics).intersection(JURISPRUDENCE_ELIGIBLE_TOPICS)
    )


def _blend_hits(primary_hits, jurisprudence_hits, limit: int, jurisprudence_quota: int = 2):
    if not jurisprudence_hits:
        return primary_hits[:limit]

    selected = []
    selected_ids = set()

    def add_hit(hit):
        if hit.fragment.id in selected_ids or len(selected) >= limit:
            return
        selected.append(hit)
        selected_ids.add(hit.fragment.id)

    reserved_for_jurisprudence = min(
        jurisprudence_quota,
        len(jurisprudence_hits),
        max(limit - 1, 0),
    )
    primary_non_jurisprudence_hits = [hit for hit in primary_hits if not _is_jurisprudence_hit(hit)]

    for hit in primary_non_jurisprudence_hits[: max(limit - reserved_for_jurisprudence, 0)]:
        add_hit(hit)
    for hit in jurisprudence_hits[:reserved_for_jurisprudence]:
        add_hit(hit)
    for hit in primary_hits:
        add_hit(hit)
    for hit in jurisprudence_hits:
        add_hit(hit)

    return selected[:limit]


def _mark_consultation_failed(consultation: Consultation, error_message: str):
    ConsultationRetrieval.objects.filter(consultation=consultation).delete()
    ConsultationCitation.objects.filter(consultation=consultation).delete()
    consultation.status = Consultation.Status.FAILED
    consultation.error_message = error_message
    consultation.final_answer = ""
    consultation.save(
        update_fields=["status", "error_message", "final_answer", "updated_at"]
    )
    return consultation


def process_consultation(consultation: Consultation):
    consultation.status = Consultation.Status.PROCESSING
    consultation.normalized_prompt = normalize_text(consultation.prompt)
    consultation.detected_matter = classify_matter(consultation.prompt)
    consultation.detected_topics_json = detect_topics(consultation.prompt)
    consultation.error_message = ""
    consultation.save(
        update_fields=[
            "status",
            "normalized_prompt",
            "detected_matter",
            "detected_topics_json",
            "error_message",
            "updated_at",
        ]
    )

    try:
        with transaction.atomic():
            if not DocumentFragment.objects.exists():
                return _mark_consultation_failed(
                    consultation,
                    (
                        "La base juridica no tiene fragmentos indexados. "
                        "Ejecuta una ingesta inicial o carga el seed antes de publicar consultas."
                    ),
                )

            queries = expand_query(
                consultation.prompt,
                consultation.detected_matter,
                consultation.detected_topics_json,
            )
            hit_groups = [retrieve_fragments(query) for query in queries]
            primary_hits = _merge_hits(hit_groups)

            jurisprudence_hits = []
            if _should_include_jurisprudence(
                consultation.detected_matter,
                consultation.detected_topics_json,
            ):
                jurisprudence_hit_groups = [
                    retrieve_fragments(
                        query,
                        limit=max(2, settings.DEFAULT_RETRIEVAL_LIMIT // 2),
                        document_type=LegalDocument.DocumentType.THESIS,
                    )
                    for query in queries
                ]
                jurisprudence_hits = _merge_hits(jurisprudence_hit_groups)

            hits = _blend_hits(
                primary_hits,
                jurisprudence_hits,
                limit=settings.DEFAULT_RETRIEVAL_LIMIT,
            )

            if not hits:
                return _mark_consultation_failed(
                    consultation,
                    (
                        "No se recuperaron fragmentos para esta consulta. "
                        "Verifica la cobertura documental o vuelve a indexar la base juridica."
                    ),
                )

            ConsultationRetrieval.objects.filter(consultation=consultation).delete()
            ConsultationCitation.objects.filter(consultation=consultation).delete()

            for rank, hit in enumerate(hits, start=1):
                ConsultationRetrieval.objects.create(
                    consultation=consultation,
                    fragment=hit.fragment,
                    score=hit.combined_score,
                    retrieval_type=hit.retrieval_type,
                    rank=rank,
                )

            provider_answer = generate_consultation_answer(
                consultation,
                hits,
                consultation.detected_matter,
                consultation.detected_topics_json,
            )

            if not provider_answer.citations:
                return _mark_consultation_failed(
                    consultation,
                    "No se encontraron citas suficientes para publicar una respuesta segura.",
                )

            for citation in provider_answer.citations:
                ConsultationCitation.objects.create(
                    consultation=consultation,
                    fragment=citation["fragment"],
                    citation_label=citation["citation_label"],
                    snippet_used=citation["snippet_used"],
                    order_index=citation["order_index"],
                )

            consultation.status = Consultation.Status.COMPLETED
            consultation.final_answer = provider_answer.answer
            consultation.model_name = provider_answer.model_name
            consultation.answer_metadata_json = {
                "provider": settings.LLM_PROVIDER,
                "expanded_queries": queries,
                "prompt_template": provider_answer.prompt_template,
                "citation_count": len(provider_answer.citations),
            }
            consultation.save(
                update_fields=[
                    "status",
                    "final_answer",
                    "model_name",
                    "answer_metadata_json",
                    "updated_at",
                ]
            )
            return consultation
    except Exception as exc:
        return _mark_consultation_failed(
            consultation,
            f"Error inesperado al procesar la consulta: {exc}",
        )
