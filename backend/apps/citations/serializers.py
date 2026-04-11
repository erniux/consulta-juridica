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
    official_url = serializers.SerializerMethodField()

    class Meta:
        model = ConsultationCitation
        fields = [
            "id",
            "fragment_id",
            "document_title",
            "digital_registry_number",
            "source_name",
            "official_url",
            "citation_label",
            "snippet_used",
            "order_index",
            "created_at",
        ]

    def get_official_url(self, obj):
        return obj.fragment.legal_document.get_public_url()
