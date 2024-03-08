from datetime import date

import stripe
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Borrowing, Payment
from .serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    ReturnActionSerializer,
    BorrowingReadonlySerializer,
    PaymentSerializer,
    PaymentListSerializer,
    PaymentDetailSerializer,

)
from library.permissions import IsAuthenticatedReadOnly, IsCurrentlyLoggedIn

from library.models import Book
from .tasks import delay_borrowing_create


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
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
        if self.action in ["update", "partial_update", "return_borrowing"]:
            return [IsCurrentlyLoggedIn()]
        if self.action == "destroy":
            return [IsAdminUser()]

        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        book_id = request.data.get("book")
        book_instance = Book.objects.get(pk=book_id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if book_instance.inventory > 0:
            book_instance.inventory -= 1
            book_instance.save()

            task_result = delay_borrowing_create.apply_async(
                args=[
                    request.user.id, book_id, serializer.data
                ],
                countdown=60
            )

            if not task_result:
                return Response(
                    {"error": "Failed to schedule task"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            payment_url = self.generate_payment_url()
            return redirect(payment_url)

        return Response(
            {"error": "This book is not currently available"},
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )

    @staticmethod
    def generate_payment_url():
        payment_url = "/api/borrowings/payments/"
        return payment_url

    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user)

    # def perform_update(self, serializer):
    #     serializer.save(user=self.request.user)

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

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response({"error": "Fail"}, status=status.HTTP_400_BAD_REQUEST)

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


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return PaymentSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [IsCurrentlyLoggedIn()]
        if self.action == "destroy":
            return [IsAdminUser()]

        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        response = self.stripe_card_payment(request.data)

        if response.get("status") == 200:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            borrowing_id = serializer.data.get("borrowing")
            if borrowing_id:
                borrowing = Borrowing.objects.get(pk=borrowing_id)

                borrowing.paid = True
                borrowing.save()
            else:
                return Response(
                    {"error": "Failed to save payment"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(response)

    def stripe_card_payment(self, request_data):
        try:
            amount = self.calculate_amount(request_data)
            currency = "usd"
            payment_intent = self.create_payment_intent(amount, currency)
            success, message = self.handle_payment_response(payment_intent)
            if success:
                return {"message": message, "status": status.HTTP_200_OK}
            else:
                return {"error": message, "status": status.HTTP_400_BAD_REQUEST}
        except Exception as e:
            return {"error": str(e), "status": status.HTTP_400_BAD_REQUEST}

    @staticmethod
    def create_payment_intent(amount, currency):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method_types=["card"],
            payment_method="pm_card_visa",
            confirm=True,
        )

        return payment_intent

    @staticmethod
    def handle_payment_response(payment_intent):
        if payment_intent.status == "succeeded":
            return True, "Payment succeeded"
        else:
            error_message = (
                payment_intent.last_payment_error
                and payment_intent.last_payment_error.message
            )
            return False, f"Payment failed: {error_message}"

    @staticmethod
    def calculate_amount(request_data):
        borrowing_id = request_data.get("borrowing")
        borrowing = Borrowing.objects.get(pk=borrowing_id)
        duration = borrowing.expected_return_date - borrowing.borrow_date
        amount_dollars = borrowing.book.daily_fee * duration.days
        amount_cents = int(amount_dollars * 100)

        return amount_cents

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
