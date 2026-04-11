from rest_framework import serializers

from .models import ConsultationCitation


class ConsultationCitationSerializer(serializers.ModelSerializer):
    fragment_id = serializers.IntegerField(source="fragment.id", read_only=True)
    document_title = serializers.CharField(source="fragment.legal_document.title", read_only=True)
    digital_registry_number = serializers.CharField(
        source="fragment.legal_document.digital_registry_number",
        read_only=True,
    )
    source_name = serializers.CharField(source="fragment.legal_document.source.name", read_only=True)

    class Meta:
        model = ConsultationCitation
        fields = [
            "id",
            "fragment_id",
            "document_title",
            "digital_registry_number",
            "source_name",
            "citation_label",
            "snippet_used",
            "order_index",
            "created_at",
        ]
