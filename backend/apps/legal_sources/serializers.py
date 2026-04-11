from rest_framework import serializers

from .models import Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            "id",
            "name",
            "slug",
            "type",
            "authority",
            "official_url",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
