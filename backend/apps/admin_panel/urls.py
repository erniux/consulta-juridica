from django.urls import path

from .views import JobListView, RunIngestionView, RunIndexingView


urlpatterns = [
    path("ingestion/run/", RunIngestionView.as_view(), name="admin_ingestion_run"),
    path("indexing/run/", RunIndexingView.as_view(), name="admin_indexing_run"),
    path("jobs/", JobListView.as_view(), name="admin_job_list"),
]
