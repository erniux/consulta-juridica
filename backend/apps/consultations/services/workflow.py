from django.conf import settings
from django.db import transaction

from common.text import normalize_text

from apps.citations.models import ConsultationCitation
from apps.legal_indexing.services.retrieval import retrieve_fragments
from apps.llm_orchestrator.services.classifiers import classify_matter, detect_topics, expand_query
from apps.llm_orchestrator.services.orchestrator import generate_consultation_answer

from ..models import Consultation, ConsultationRetrieval


def _merge_hits(hit_groups):
    merged = {}
    for hits in hit_groups:
        for hit in hits:
            current = merged.get(hit.fragment.id)
            if current is None or hit.combined_score > current.combined_score:
                merged[hit.fragment.id] = hit
    return sorted(merged.values(), key=lambda item: item.combined_score, reverse=True)


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
            queries = expand_query(
                consultation.prompt,
                consultation.detected_matter,
                consultation.detected_topics_json,
            )
            hit_groups = [retrieve_fragments(query) for query in queries]
            hits = _merge_hits(hit_groups)[: settings.DEFAULT_RETRIEVAL_LIMIT]

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
