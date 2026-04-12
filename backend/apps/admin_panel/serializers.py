from rest_framework import serializers

from apps.legal_indexing.models import IngestionJob


class JobRunSerializer(serializers.Serializer):
    source_id = serializers.IntegerField(required=False)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=False,
    )
    official_source_slugs = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    jurisprudence_queries = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    jurisprudence_prompt = serializers.CharField(required=False, allow_blank=False)
    jurisprudence_max_results = serializers.IntegerField(required=False, min_value=1, max_value=25)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        ingestion_modes = [
            bool(attrs.get("document_ids")),
            bool(attrs.get("official_source_slugs")),
            bool(attrs.get("jurisprudence_queries")),
            bool(attrs.get("jurisprudence_prompt")),
        ]
        if sum(1 for enabled in ingestion_modes if enabled) > 1:
            raise serializers.ValidationError(
                (
                    "Use a single ingestion mode per job: document_ids, official_source_slugs, "
                    "jurisprudence_queries o jurisprudence_prompt."
                )
            )
        return attrs


class JobSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            "id",
            "job_type",
            "status",
            "source",
            "source_name",
            "notes",
            "error_message",
            "payload_json",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
