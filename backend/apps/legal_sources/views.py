from rest_framework import generics

from .models import Source
from .serializers import SourceSerializer


class SourceListView(generics.ListAPIView):
    queryset = Source.objects.filter(is_active=True).order_by("name")
    serializer_class = SourceSerializer
