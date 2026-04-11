from django.contrib import admin

from .models import LegalDocument


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "short_name",
        "document_type",
        "subject_area",
        "is_current",
        "updated_at",
    )
    list_filter = ("document_type", "subject_area", "is_current")
    search_fields = ("title", "short_name", "version_label")
