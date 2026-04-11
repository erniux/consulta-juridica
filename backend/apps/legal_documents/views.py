from django.db.models import Count, Q
from rest_framework import generics

from .models import LegalDocument
from .serializers import LegalDocumentDetailSerializer, LegalDocumentListSerializer


class LegalDocumentListView(generics.ListAPIView):
    serializer_class = LegalDocumentListSerializer

    def get_queryset(self):
        queryset = LegalDocument.objects.select_related("source").annotate(
            fragment_count=Count("fragments")
        )
        document_type = self.request.query_params.get("document_type")
        subject_area = self.request.query_params.get("subject_area")
        query = self.request.query_params.get("q")

        if document_type:
            queryset = queryset.filter(document_type=document_type)
        if subject_area:
            queryset = queryset.filter(subject_area=subject_area)
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(short_name__icontains=query)
                | Q(digital_registry_number__icontains=query)
            )
        return queryset.order_by("title")


class LegalDocumentDetailView(generics.RetrieveAPIView):
    queryset = LegalDocument.objects.select_related("source").prefetch_related("fragments")
    serializer_class = LegalDocumentDetailSerializer
