from datetime import datetime, date

from django.db import Error
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Borrowing
from .serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
)
from library.permissions import IsAuthenticatedReadOnly, IsCurrentlyLoggedIn

from library.models import Book


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "retrieve":
            return BorrowingDetailSerializer

        return BorrowingSerializer

    def get_permissions(self):
        if self.action == "update":
            return [IsCurrentlyLoggedIn()]
        if self.action == "destroy":
            return [IsAdminUser()]

        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        book_id = request.data.get("book")
        book_instance = Book.objects.get(pk=book_id)

        if book_instance.inventory > 0:
            book_instance.inventory -= 1
            book_instance.save()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

        return Response(
            {"error": "This book is not currently available"},
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.query_params.get("user")
        is_active = self.request.query_params.get("is_active")
        queryset = self.queryset

        if user:
            user_id = int(user)
            queryset = queryset.filter(user__id=user_id)

        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(returned__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(returned__isnull=False)
            else:
                return Borrowing.objects.none()

        return queryset
