from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Consultation(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="consultations",
        on_delete=models.CASCADE,
    )
    prompt = models.TextField()
    normalized_prompt = models.TextField(blank=True)
    detected_matter = models.CharField(max_length=64, blank=True)
    detected_topics_json = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.QUEUED)
    final_answer = models.TextField(blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    answer_metadata_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Consultation #{self.pk}"


class ConsultationRetrieval(TimeStampedModel):
    class RetrievalType(models.TextChoices):
        KEYWORD = "keyword", "Keyword"
        SEMANTIC = "semantic", "Semantic"
        HYBRID = "hybrid", "Hybrid"

    consultation = models.ForeignKey(
        Consultation,
        related_name="retrievals",
        on_delete=models.CASCADE,
    )
    fragment = models.ForeignKey(
        "legal_indexing.DocumentFragment",
        related_name="consultation_retrievals",
        on_delete=models.CASCADE,
    )
    score = models.FloatField()
    retrieval_type = models.CharField(max_length=32, choices=RetrievalType.choices)
    rank = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["rank", "id"]
        unique_together = ("consultation", "fragment")

    def __str__(self):
        return f"{self.consultation_id} -> {self.fragment_id}"
