from common.tasking import shared_task

from .models import IngestionJob
from .services.ingestion import run_ingestion_job
from .services.indexing import reindex_documents


@shared_task
def run_ingestion_job_task(job_id: int):
    job = IngestionJob.objects.select_related("source").get(pk=job_id)
    return run_ingestion_job(job)


@shared_task
def run_indexing_job_task(job_id: int):
    job = IngestionJob.objects.select_related("source").get(pk=job_id)
    job.mark_processing()
    try:
        queryset = job.get_target_documents()
        reindex_documents(queryset)
        job.mark_completed(f"Indexed documents: {queryset.count()}")
    except Exception as exc:  # pragma: no cover - defensive runtime path.
        job.mark_failed(str(exc))
    return job.id
