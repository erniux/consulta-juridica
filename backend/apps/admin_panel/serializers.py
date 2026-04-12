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
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get("document_ids") and attrs.get("official_source_slugs"):
            raise serializers.ValidationError(
                "Use document_ids or official_source_slugs, but not both in the same job."
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
