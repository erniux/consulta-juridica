from rest_framework import serializers

from apps.citations.serializers import ConsultationCitationSerializer
from common.text import normalize_text

from .models import Consultation, ConsultationRetrieval


class ConsultationCreateSerializer(serializers.Serializer):
    prompt = serializers.CharField()


class ConsultationRetrievalSerializer(serializers.ModelSerializer):
    fragment = serializers.SerializerMethodField()

    class Meta:
        model = ConsultationRetrieval
        fields = ["id", "score", "retrieval_type", "rank", "fragment", "created_at"]

    def get_fragment(self, obj):
        legal_document = obj.fragment.legal_document
        source = legal_document.source
        return {
            "id": obj.fragment_id,
            "title": obj.fragment.title,
            "article_number": obj.fragment.article_number,
            "document_title": legal_document.title,
            "source_name": source.name,
            "official_url": legal_document.official_url or source.official_url,
        }


class ConsultationListSerializer(serializers.ModelSerializer):
    citation_count = serializers.IntegerField(read_only=True)
    group_key = serializers.SerializerMethodField()

    class Meta:
        model = Consultation
        fields = [
            "id",
            "prompt",
            "detected_matter",
            "status",
            "citation_count",
            "group_key",
            "created_at",
            "updated_at",
        ]

    def get_group_key(self, obj):
        return obj.normalized_prompt or normalize_text(obj.prompt)


class ConsultationDetailSerializer(serializers.ModelSerializer):
    retrievals = ConsultationRetrievalSerializer(many=True, read_only=True)
    citations = ConsultationCitationSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            "id",
            "prompt",
            "detected_matter",
            "detected_topics_json",
            "status",
            "final_answer",
            "model_name",
            "answer_metadata_json",
            "error_message",
            "retrievals",
            "citations",
            "created_at",
            "updated_at",
        ]
