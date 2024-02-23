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
