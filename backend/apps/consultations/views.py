from django.conf import settings
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Consultation
from .serializers import (
    ConsultationCreateSerializer,
    ConsultationDetailSerializer,
    ConsultationListSerializer,
)
from .services.workflow import process_consultation
from .tasks import process_consultation_task


class ConsultationListCreateView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ConsultationCreateSerializer
        return ConsultationListSerializer

    def get_queryset(self):
        queryset = Consultation.objects.annotate(citation_count=Count("citations")).order_by(
            "-created_at"
        )
        if self.request.user.is_superuser or getattr(self.request.user, "role", "") == "admin":
            return queryset
        return queryset.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consultation = Consultation.objects.create(
            user=request.user,
            prompt=serializer.validated_data["prompt"],
            status=Consultation.Status.QUEUED,
        )

        if settings.ASYNC_CONSULTATIONS:
            process_consultation_task.delay(consultation.id)
            consultation.refresh_from_db()
            payload = ConsultationDetailSerializer(consultation).data
            return Response(payload, status=status.HTTP_202_ACCEPTED)

        process_consultation(consultation)
        consultation.refresh_from_db()
        payload = ConsultationDetailSerializer(consultation).data
        return Response(payload, status=status.HTTP_201_CREATED)


class ConsultationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ConsultationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Consultation.objects.prefetch_related(
            "retrievals__fragment__legal_document__source",
            "citations__fragment__legal_document__source",
        )
        if self.request.user.is_superuser or getattr(self.request.user, "role", "") == "admin":
            return queryset
        return queryset.filter(user=self.request.user)
