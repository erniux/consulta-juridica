from django.contrib import admin

from .models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "authority", "is_active", "updated_at")
    list_filter = ("type", "is_active", "authority")
    search_fields = ("name", "authority", "official_url")
    prepopulated_fields = {"slug": ("name",)}
