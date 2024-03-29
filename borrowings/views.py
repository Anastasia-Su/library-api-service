from datetime import date

import stripe
from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Borrowing, Payment, Fines
from .serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    ReturnActionSerializer,
    BorrowingReadonlySerializer,
    PaymentSerializer,
    PaymentListSerializer,
    PaymentDetailSerializer,
    PaymentCreateSerializer,
    RefundActionSerializer,
    FinesSerializer,
    FinesListSerializer,
    FinesDetailSerializer,
    FinesCreateSerializer,
)
from library.permissions import IsAuthenticatedReadOnly, IsCurrentlyLoggedIn

from library.models import Book
from .tasks import delay_borrowing_create, notify_about_borrowing_create
from .utils import stripe_card_payment, calculate_fines, calculate_amount


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.select_related("user__profile", "book")
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if not self.request.user.is_authenticated:
            return BorrowingReadonlySerializer
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        if self.action == "return_borrowing":
            return ReturnActionSerializer
        return BorrowingSerializer

    def get_permissions(self):
        if self.action == "return_borrowing":
            return [IsCurrentlyLoggedIn()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAdminUser()]

        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        if serializer.instance.book.inventory > 0:
            return redirect("borrowings:payments-list")

        return Response(
            {"error": "This book is not currently available"},
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        methods=["POST"],
        detail=True,
        url_path="return-borrowing",
    )
    def return_borrowing(self, request, pk):
        """Endpoint for returning a borrowing"""
        borrowing = self.get_object()

        if request.method == "POST":
            if borrowing.returned is not None:
                return Response(
                    {"error": "This book is already returned"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            borrowing.returned = date.today()

            serializer = self.get_serializer(borrowing, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            book_id = borrowing.book.id
            book_instance = Book.objects.get(pk=book_id)

            book_instance.inventory += 1
            book_instance.save()

            if borrowing.expected_return_date < date.today():
                # IF YOU DON't USE CELERY, PLEASE UNCOMMENT FOLLOWING TWO LINES

                # borrowing.fines_applied = calculate_fines(borrowing.id)
                # borrowing.save()

                return redirect("borrowings:fines-list")

            return Response(
                {"success": "Borrowing returned"}, status=status.HTTP_201_CREATED
            )

        return Response({"error": "Fail"}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        user = self.request.query_params.get("user")
        returned = self.request.query_params.get("returned")
        fines = self.request.query_params.get("fines")

        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                user=self.request.user,
                paid=True,
                cancelled=False,
                returned__isnull=True,
            )

        if user:
            user_id = int(user)
            queryset = queryset.filter(user__id=user_id)

        if returned:
            if returned.lower() == "true":
                queryset = queryset.filter(returned__isnull=False)
            elif returned.lower() == "false":
                queryset = queryset.filter(returned__isnull=True)
            else:
                return Borrowing.objects.none()

        if fines:
            if fines.lower() == "true":
                queryset = queryset.filter(fines_applied__isnull=False)
            elif fines.lower() == "false":
                queryset = queryset.filter(fines_applied__isnull=True)
            else:
                return Borrowing.objects.none()

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "user",
                type=OpenApiTypes.INT,
                description="Filter by user id (ex. ?user=2)",
            ),
            OpenApiParameter(
                "returned",
                type=OpenApiTypes.BOOL,
                description="Filter by returned status (ex. ?returned=true)",
            ),
            OpenApiParameter(
                "fines",
                type=OpenApiTypes.BOOL,
                description="Filter by fines presence (ex. ?fines=false)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("user__profile", "borrowing")
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        if self.action == "retrieve":
            return PaymentDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return PaymentCreateSerializer
        if self.action == "refund_payment":
            return RefundActionSerializer

        return PaymentSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticatedReadOnly()]
        if self.action == "destroy":
            return [IsAdminUser()]
        if self.action == "refund_payment":
            return [IsCurrentlyLoggedIn()]

        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        borrowing_id = request.data.get("borrowing")

        if borrowing_id:
            response = stripe_card_payment(borrowing_id, calculate_amount)

            if response.get("status") == 200:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                serializer.instance.amount_paid = calculate_amount(borrowing_id)
                serializer.instance.stripe_payment_id = response["stripe_payment_id"]
                serializer.instance.save()

                borrowing = Borrowing.objects.get(pk=borrowing_id)

                borrowing.paid = True
                borrowing.payment = serializer.instance
                borrowing.stripe_payment_id = response["stripe_payment_id"]
                borrowing.save()

                book_instance = Book.objects.get(
                    pk=serializer.instance.borrowing.book.id
                )
                book_instance.inventory -= 1
                book_instance.save()

                task_result = notify_about_borrowing_create.apply_async(
                    args=[borrowing_id, request.user.id], countdown=0
                )

                if not task_result:
                    return Response(
                        {"error": "Failed to schedule task"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            return Response(response)

        return Response(
            {"error": "No borrowing found"}, status=status.HTTP_404_NOT_FOUND
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        methods=["POST"],
        detail=True,
        url_path="refund-payment",
    )
    def refund_payment(self, request, pk):
        """Endpoint for refunding costs for a borrowing"""
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if request.method == "POST":
            payment = get_object_or_404(Payment, pk=pk)
            borrowing = get_object_or_404(Borrowing, pk=payment.borrowing.id)
            payment_intent_id = payment.stripe_payment_id

            if borrowing.borrow_date != date.today():
                return Response(
                    {"denied": "You can only refund borrowings created today"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                if payment_intent_id:
                    refund = stripe.Refund.create(payment_intent=payment_intent_id)
                    if refund:
                        payment.refunded = True
                        borrowing.cancelled = True
                        borrowing.save()
                        payment.save()

                        return Response(
                            {"message": "Refund created"}, status=status.HTTP_200_OK
                        )

            except stripe.error.StripeError as e:
                print("Stripe error:", str(e))
                return Response(
                    {"error": "Failed to create refund: " + str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST
        )

    def get_queryset(self):
        user = self.request.query_params.get("user")
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        if user:
            user_id = int(user)
            queryset = queryset.filter(user__id=user_id)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "user",
                type=OpenApiTypes.INT,
                description="Filter by user id (ex. ?user=2)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FinesViewSet(viewsets.ModelViewSet):
    queryset = Fines.objects.select_related("user__profile", "borrowing")
    serializer_class = FinesSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return FinesListSerializer
        if self.action == "retrieve":
            return FinesDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return FinesCreateSerializer

        return FinesSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticatedReadOnly()]
        if self.action == "destroy":
            return [IsAdminUser()]

        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        borrowing_id = request.data.get("borrowing")
        borrowing = Borrowing.objects.get(pk=borrowing_id)

        if borrowing_id:
            response = stripe_card_payment(borrowing_id, calculate_fines)

            if response.get("status") == 200:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                payment = borrowing.payment

                serializer.instance.fines_paid = calculate_fines(borrowing_id)
                serializer.instance.stripe_payment_id = response["stripe_payment_id"]

                if payment:
                    serializer.instance.payment = payment
                    serializer.instance.save()
                    print("serpay", serializer.instance.payment)

                    payment.fines = serializer.instance
                else:
                    return Response(
                        {"error": "No payment found"}, status=status.HTTP_404_NOT_FOUND
                    )

                borrowing.fines_paid = True
                borrowing.stripe_payment_id = response["stripe_payment_id"]

                borrowing.save()
                payment.save()

            return Response(response)

        return Response(
            {"error": "No borrowing found"}, status=status.HTTP_404_NOT_FOUND
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.query_params.get("user")
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        if user:
            user_id = int(user)
            queryset = queryset.filter(user__id=user_id)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "user",
                type=OpenApiTypes.INT,
                description="Filter by user id (ex. ?user=2)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
