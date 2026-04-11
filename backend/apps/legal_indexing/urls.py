from django.urls import path

from .views import DocumentFragmentDetailView, SearchJurisprudenceView, SearchLegalView


urlpatterns = [
    path("fragments/<int:pk>/", DocumentFragmentDetailView.as_view(), name="fragment_detail"),
    path("search/legal/", SearchLegalView.as_view(), name="search_legal"),
    path("search/jurisprudence/", SearchJurisprudenceView.as_view(), name="search_jurisprudence"),
]
