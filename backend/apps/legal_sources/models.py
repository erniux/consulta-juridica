from django.db import models

from common.models import TimeStampedModel


class Source(TimeStampedModel):
    class SourceType(models.TextChoices):
        LAW = "law", "Law"
        JURISPRUDENCE = "jurisprudence", "Jurisprudence"
        GAZETTE = "gazette", "Gazette"
        REGULATION = "regulation", "Regulation"

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    type = models.CharField(max_length=32, choices=SourceType.choices)
    authority = models.CharField(max_length=255)
    official_url = models.URLField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
