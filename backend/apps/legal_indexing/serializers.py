from rest_framework import serializers

from .models import DocumentFragment, IngestionJob, LegalTopic


class LegalTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalTopic
        fields = ["id", "name", "slug", "description"]


class DocumentFragmentSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="legal_document.title", read_only=True)
    source_name = serializers.CharField(source="legal_document.source.name", read_only=True)
    digital_registry_number = serializers.CharField(
        source="legal_document.digital_registry_number",
        read_only=True,
    )
    official_url = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFragment
        fields = [
            "id",
            "document_title",
            "source_name",
            "digital_registry_number",
            "official_url",
            "fragment_type",
            "article_number",
            "section_path",
            "title",
            "content",
            "metadata_json",
            "topics",
            "created_at",
            "updated_at",
        ]

    def get_topics(self, obj):
        return [relation.topic.slug for relation in obj.topic_relations.select_related("topic")]

    def get_official_url(self, obj):
        return obj.legal_document.get_public_url()


class IngestionJobSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    requested_by = serializers.CharField(source="requested_by.username", read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            "id",
            "job_type",
            "status",
            "source",
            "source_name",
            "requested_by",
            "notes",
            "error_message",
            "payload_json",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
