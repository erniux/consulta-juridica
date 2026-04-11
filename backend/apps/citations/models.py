from django.db import models

from common.models import TimeStampedModel


class ConsultationCitation(TimeStampedModel):
    consultation = models.ForeignKey(
        "consultations.Consultation",
        related_name="citations",
        on_delete=models.CASCADE,
    )
    fragment = models.ForeignKey(
        "legal_indexing.DocumentFragment",
        related_name="consultation_citations",
        on_delete=models.CASCADE,
    )
    citation_label = models.CharField(max_length=255)
    snippet_used = models.TextField()
    order_index = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order_index", "id"]

    def __str__(self):
        return self.citation_label
