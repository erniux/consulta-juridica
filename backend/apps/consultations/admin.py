from django.contrib import admin

from .models import Consultation, ConsultationRetrieval


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "detected_matter", "status", "created_at")
    list_filter = ("status", "detected_matter")
    search_fields = ("prompt", "final_answer", "user__username")


@admin.register(ConsultationRetrieval)
class ConsultationRetrievalAdmin(admin.ModelAdmin):
    list_display = ("consultation", "fragment", "score", "retrieval_type", "rank")
    list_filter = ("retrieval_type",)
