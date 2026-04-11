from django.conf import settings
from django.db import models
from django.utils import timezone

from common.db_fields import VectorField
from common.models import TimeStampedModel


class DocumentFragment(TimeStampedModel):
    class FragmentType(models.TextChoices):
        ARTICLE = "article", "Article"
        FRACTION = "fraction", "Fraction"
        CHAPTER = "chapter", "Chapter"
        THESIS = "thesis", "Thesis"
        RUBRO = "rubro", "Rubro"
        PRECEDENT = "precedent", "Precedent"
        SECTION = "section", "Section"

    legal_document = models.ForeignKey(
        "legal_documents.LegalDocument",
        related_name="fragments",
        on_delete=models.CASCADE,
    )
    fragment_type = models.CharField(max_length=32, choices=FragmentType.choices)
    article_number = models.CharField(max_length=32, blank=True)
    section_path = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    normalized_content = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    order_index = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["legal_document", "order_index", "id"]
        indexes = [
            models.Index(fields=["fragment_type"]),
            models.Index(fields=["article_number"]),
        ]

    def __str__(self):
        return f"{self.legal_document.short_name} - {self.title}"


class DocumentEmbedding(TimeStampedModel):
    fragment = models.OneToOneField(
        DocumentFragment,
        related_name="embedding",
        on_delete=models.CASCADE,
    )
    embedding = VectorField(dimensions=16, null=True, blank=True)
    model_name = models.CharField(max_length=120)
    metadata_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Embedding for {self.fragment_id}"


class LegalTopic(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FragmentTopic(TimeStampedModel):
    fragment = models.ForeignKey(
        DocumentFragment,
        related_name="topic_relations",
        on_delete=models.CASCADE,
    )
    topic = models.ForeignKey(
        LegalTopic,
        related_name="fragment_relations",
        on_delete=models.CASCADE,
    )
    confidence = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("fragment", "topic")

    def __str__(self):
        return f"{self.fragment_id} -> {self.topic.slug}"


class IngestionJob(TimeStampedModel):
    class JobType(models.TextChoices):
        INGESTION = "ingestion", "Ingestion"
        INDEXING = "indexing", "Indexing"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        "legal_sources.Source",
        related_name="jobs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ingestion_jobs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.QUEUED)
    notes = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    payload_json = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job_type} #{self.pk}"

    def get_target_documents(self):
        from apps.legal_documents.models import LegalDocument

        queryset = LegalDocument.objects.all()
        document_ids = self.payload_json.get("document_ids", []) if self.payload_json else []
        if document_ids:
            return queryset.filter(id__in=document_ids)
        if self.source_id:
            return queryset.filter(source_id=self.source_id)
        return queryset

    def mark_processing(self):
        self.status = self.Status.PROCESSING
        self.started_at = timezone.now()
        self.error_message = ""
        self.save(update_fields=["status", "started_at", "error_message", "updated_at"])

    def mark_completed(self, notes: str = ""):
        self.status = self.Status.COMPLETED
        self.finished_at = timezone.now()
        self.notes = notes or self.notes
        self.save(update_fields=["status", "finished_at", "notes", "updated_at"])

    def mark_failed(self, error_message: str):
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
