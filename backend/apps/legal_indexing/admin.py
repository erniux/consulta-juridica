from django.contrib import admin

from .models import DocumentEmbedding, DocumentFragment, FragmentTopic, IngestionJob, LegalTopic


@admin.register(DocumentFragment)
class DocumentFragmentAdmin(admin.ModelAdmin):
    list_display = ("title", "legal_document", "fragment_type", "article_number", "order_index")
    list_filter = ("fragment_type", "legal_document__document_type")
    search_fields = ("title", "content", "section_path", "article_number")


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("fragment", "model_name", "created_at")
    search_fields = ("fragment__title", "model_name")


@admin.register(LegalTopic)
class LegalTopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(FragmentTopic)
class FragmentTopicAdmin(admin.ModelAdmin):
    list_display = ("fragment", "topic", "confidence")
    list_filter = ("topic",)


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "job_type", "status", "source", "requested_by", "created_at")
    list_filter = ("job_type", "status")
    search_fields = ("notes", "error_message", "source__name")
