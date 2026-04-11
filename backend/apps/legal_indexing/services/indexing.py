from collections import defaultdict

from django.conf import settings
from django.db import transaction

from common.text import deterministic_embedding, normalize_text

from ..models import DocumentEmbedding, FragmentTopic, LegalTopic


TOPIC_RULES = {
    "riesgo-de-trabajo": ["riesgo", "accidente", "incapacidad", "trabajo"],
    "renuncia-forzada": ["renuncia", "presion", "firma", "patron"],
    "seguridad-social": ["imss", "seguro", "social", "incapacidad"],
    "despido": ["despido", "rescicion", "separacion", "terminacion"],
}


def get_or_create_topics():
    topics = {}
    for slug in TOPIC_RULES:
        topic, _ = LegalTopic.objects.get_or_create(
            slug=slug,
            defaults={"name": slug.replace("-", " ").title(), "description": ""},
        )
        topics[slug] = topic
    return topics


@transaction.atomic
def index_fragments(fragments):
    topics = get_or_create_topics()
    indexed = []

    for fragment in fragments:
        normalized_content = normalize_text(fragment.content)
        if fragment.normalized_content != normalized_content:
            fragment.normalized_content = normalized_content
            fragment.save(update_fields=["normalized_content", "updated_at"])

        vector = deterministic_embedding(fragment.content, settings.VECTOR_DIMENSIONS)
        DocumentEmbedding.objects.update_or_create(
            fragment=fragment,
            defaults={
                "embedding": vector,
                "model_name": settings.EMBEDDING_MODEL,
                "metadata_json": {"strategy": "deterministic-mock"},
            },
        )

        FragmentTopic.objects.filter(fragment=fragment).delete()
        for slug, keywords in TOPIC_RULES.items():
            matches = [keyword for keyword in keywords if keyword in normalized_content]
            if not matches:
                continue
            FragmentTopic.objects.create(
                fragment=fragment,
                topic=topics[slug],
                confidence=min(1.0, 0.35 + (0.15 * len(matches))),
            )

        indexed.append(fragment)

    return indexed


def reindex_documents(documents):
    fragments = []
    for document in documents:
        fragments.extend(list(document.fragments.all()))
    return index_fragments(fragments)
