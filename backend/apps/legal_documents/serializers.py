from rest_framework import serializers

from .models import LegalDocument


class LegalDocumentListSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    fragment_count = serializers.IntegerField(read_only=True)
    official_url = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = [
            "id",
            "title",
            "short_name",
            "document_type",
            "digital_registry_number",
            "jurisdiction",
            "subject_area",
            "last_reform_date",
            "version_label",
            "is_current",
            "source_name",
            "fragment_count",
            "official_url",
            "updated_at",
        ]

    def get_official_url(self, obj):
        return obj.get_public_url()


class LegalDocumentDetailSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()
    fragments = serializers.SerializerMethodField()
    official_url = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = [
            "id",
            "title",
            "short_name",
            "document_type",
            "digital_registry_number",
            "jurisdiction",
            "subject_area",
            "publication_date",
            "effective_date",
            "last_reform_date",
            "version_label",
            "official_url",
            "raw_text",
            "metadata_json",
            "is_current",
            "source",
            "fragments",
            "created_at",
            "updated_at",
        ]

    def get_source(self, obj):
        return {
            "id": obj.source_id,
            "name": obj.source.name,
            "type": obj.source.type,
            "authority": obj.source.authority,
            "official_url": obj.source.official_url,
        }

    def get_official_url(self, obj):
        return obj.get_public_url()

    def get_fragments(self, obj):
        from apps.legal_indexing.serializers import DocumentFragmentSerializer

        fragments = obj.fragments.order_by("order_index", "id")
        return DocumentFragmentSerializer(fragments, many=True).data
