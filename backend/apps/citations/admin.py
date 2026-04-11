from django.contrib import admin

from .models import ConsultationCitation


@admin.register(ConsultationCitation)
class ConsultationCitationAdmin(admin.ModelAdmin):
    list_display = ("citation_label", "consultation", "fragment", "order_index")
    search_fields = ("citation_label", "snippet_used")
