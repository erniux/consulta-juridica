from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.legal_indexing.models import IngestionJob
from apps.legal_indexing.tasks import run_indexing_job_task, run_ingestion_job_task

from .serializers import JobRunSerializer, JobSerializer


class IsAdminOrResearcher(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", "") in {"admin", "researcher"}
        )


class BaseRunJobView(APIView):
    permission_classes = [IsAdminOrResearcher]
    job_type = None
    task = None

    def post(self, request):
        serializer = JobRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = IngestionJob.objects.create(
            source_id=serializer.validated_data.get("source_id"),
            requested_by=request.user,
            job_type=self.job_type,
            status=IngestionJob.Status.QUEUED,
            notes=serializer.validated_data.get("notes", ""),
            payload_json={"document_ids": serializer.validated_data.get("document_ids", [])},
        )

        if settings.ASYNC_ADMIN_JOBS:
            self.task.delay(job.id)
        else:
            self.task(job.id)
            job.refresh_from_db()

        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)


class RunIngestionView(BaseRunJobView):
    job_type = IngestionJob.JobType.INGESTION
    task = staticmethod(run_ingestion_job_task)


class RunIndexingView(BaseRunJobView):
    job_type = IngestionJob.JobType.INDEXING
    task = staticmethod(run_indexing_job_task)


class JobListView(generics.ListAPIView):
    permission_classes = [IsAdminOrResearcher]
    serializer_class = JobSerializer
    queryset = IngestionJob.objects.select_related("source").all()
