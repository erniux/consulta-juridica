from django.db import models

from common.models import TimeStampedModel


class LegalDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        LAW = "law", "Law"
        REGULATION = "regulation", "Regulation"
        THESIS = "thesis", "Thesis"
        PRECEDENT = "precedent", "Precedent"
        CRITERION = "criterion", "Criterion"

    class SubjectArea(models.TextChoices):
        LABOR = "labor_individual", "Labor Individual"
        SOCIAL_SECURITY = "social_security", "Social Security"
        OCCUPATIONAL_RISK = "occupational_risk", "Occupational Risk"
        GENERAL = "general", "General"

    source = models.ForeignKey(
        "legal_sources.Source",
        related_name="documents",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)
    document_type = models.CharField(
        max_length=32,
        choices=DocumentType.choices,
        default=DocumentType.LAW,
    )
    jurisdiction = models.CharField(max_length=100, default="federal")
    subject_area = models.CharField(
        max_length=32,
        choices=SubjectArea.choices,
        default=SubjectArea.GENERAL,
    )
    publication_date = models.DateField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    last_reform_date = models.DateField(null=True, blank=True)
    version_label = models.CharField(max_length=100, blank=True)
    digital_registry_number = models.CharField(max_length=32, blank=True)
    official_url = models.URLField(blank=True)
    raw_text = models.TextField()
    metadata_json = models.JSONField(default=dict, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        unique_together = ("source", "title", "version_label")
        indexes = [
            models.Index(fields=["document_type"]),
            models.Index(fields=["digital_registry_number"]),
        ]

    def __str__(self):
        return self.title
