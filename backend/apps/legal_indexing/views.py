from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DocumentFragment
from .serializers import DocumentFragmentSerializer
from .services.retrieval import document_type_for_search, retrieve_fragments


class SearchSerializer(serializers.Serializer):
    query = serializers.CharField()
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20)


class DocumentFragmentDetailView(generics.RetrieveAPIView):
    queryset = DocumentFragment.objects.select_related("legal_document", "legal_document__source")
    serializer_class = DocumentFragmentSerializer


class BaseSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    scope = "legal"

    def post(self, request):
        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hits = retrieve_fragments(
            serializer.validated_data["query"],
            limit=serializer.validated_data.get("limit"),
            document_type=document_type_for_search(self.scope),
        )
        payload = [
            {
                "score": hit.combined_score,
                "retrieval_type": hit.retrieval_type,
                "fragment": DocumentFragmentSerializer(hit.fragment).data,
            }
            for hit in hits
        ]
        return Response({"results": payload})


class SearchLegalView(BaseSearchView):
    scope = "legal"


class SearchJurisprudenceView(BaseSearchView):
    scope = "jurisprudence"
