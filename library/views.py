from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import (
    Book,
)

from .serializers import (
    BookSerializer,
    BookListSerializer,
    BookDetailSerializer,
)

from .permissions import (
    IsCurrentlyLoggedIn,
    IsAuthenticatedReadOnly,
)


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return BookListSerializer
        if self.action == "retrieve":
            return BookDetailSerializer

        return BookSerializer

    def get_permissions(self):
        if self.action in ["update", "destroy", "create"]:
            return [IsAdminUser()]

        return [IsAuthenticatedReadOnly()]

    def get_queryset(self):
        title = self.request.query_params.get("title")
        queryset = self.queryset.all()

        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "title",
                type=OpenApiTypes.STR,
                description="Filter books by title (ex. ?title=book1)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
