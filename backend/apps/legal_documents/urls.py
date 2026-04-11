from django.urls import path

from .views import LegalDocumentDetailView, LegalDocumentListView


urlpatterns = [
    path("", LegalDocumentListView.as_view(), name="document_list"),
    path("<int:pk>/", LegalDocumentDetailView.as_view(), name="document_detail"),
]
