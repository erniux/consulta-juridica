from django.contrib import admin
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthcheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "consulta-juridica-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthcheckView.as_view(), name="healthcheck"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/consultations/", include("apps.consultations.urls")),
    path("api/sources/", include("apps.legal_sources.urls")),
    path("api/documents/", include("apps.legal_documents.urls")),
    path("api/", include("apps.legal_indexing.urls")),
    path("api/admin/", include("apps.admin_panel.urls")),
]
