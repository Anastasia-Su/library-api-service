from datetime import date, datetime

from django.db.models import Q
from rest_framework import serializers
from .models import Borrowing, Payment, Fines
from .utils import calculate_amount, stripe_card_payment, calculate_fines


class BorrowingSerializer(serializers.ModelSerializer):
    def validate_borrow_date(self, value):
        request = self.context.get("request")
        if request.method == "POST" and value < date.today():
            raise serializers.ValidationError(
                "Borrow date cannot be earlier than today."
            )
        return value

    def validate_expected_return_date(self, value):
        request = self.context.get("request")

        borrow_date_str = self.initial_data.get("borrow_date")
        borrow_date = datetime.strptime(borrow_date_str, "%Y-%m-%d").date()

        if request.method == "POST" and value < date.today():
            raise serializers.ValidationError(
                "Expected return date cannot be earlier than today"
            )
        if value < borrow_date:
            raise serializers.ValidationError(
                "Expected return date cannot be earlier than borrow date"
            )
        return value

    class Meta:
        model = Borrowing
        fields = ["id", "book", "borrow_date", "expected_return_date"]


class BorrowingReadonlySerializer(BorrowingSerializer):
    class Meta:
        model = Borrowing
        fields = []


class BorrowingListSerializer(BorrowingSerializer):
    book = serializers.StringRelatedField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    borrowed = serializers.SerializerMethodField(read_only=True)

    def get_borrowed(self, obj):
        return f"from {obj.borrow_date} to {obj.expected_return_date}"

    def get_user(self, obj):
        return f"{obj.user.profile.full_name} ({obj.user.email})"

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "user",
            "book",
            "borrowed",
            "paid",
            "payment",
            "stripe_payment_id",
            "returned",
            "cancelled",
            "fines_applied",
            "fines_paid",
        ]


class BorrowingDetailSerializer(BorrowingSerializer):
    book = serializers.StringRelatedField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    def get_user(self, obj):
        return f"{obj.user.profile.full_name} ({obj.user.email})"

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "user",
            "book",
            "borrow_date",
            "expected_return_date",
            "paid",
            "payment",
            "stripe_payment_id",
            "returned",
            "cancelled",
            "fines_applied",
            "fines_paid",
        ]


class ReturnActionSerializer(BorrowingSerializer):
    to_return = serializers.ChoiceField(choices=["I return it"])

    class Meta:
        model = Borrowing
        fields = ["to_return"]


class PaymentSerializer(serializers.ModelSerializer):
    amount_paid = serializers.DecimalField(max_digits=6, decimal_places=2)
    stripe_payment_id = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("context").get("request")

        if request.user and "borrowing" in self.fields:
            self.fields["borrowing"].queryset = Borrowing.objects.filter(
                user=request.user, paid=False
            )

    def create(self, validated_data):
        borrowing = validated_data.get("borrowing")

        amount_paid = calculate_amount(borrowing.id)
        response = stripe_card_payment(borrowing.id, calculate_amount)

        validated_data["amount_paid"] = amount_paid
        validated_data["stripe_payment_id"] = response["stripe_payment_id"]

        return super().create(validated_data)

    class Meta:
        model = Payment
        fields = [
            "id",
            "card_number",
            "expiry_month",
            "expiry_year",
            "cvc",
            "borrowing",
            "amount_paid",
            "stripe_payment_id",
        ]


class PaymentListSerializer(PaymentSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_user(obj):
        return f"{obj.user.profile.full_name} ({obj.user.email})"

    class Meta:
        model = Payment
        fields = [
            "id",
            "borrowing",
            "user",
            "amount_paid",
            "stripe_payment_id",
            "refunded",
            "fines",
        ]


class PaymentDetailSerializer(PaymentListSerializer):
    borrowing = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "borrowing",
            "user",
            "amount_paid",
            "stripe_payment_id",
            "refunded",
            "fines",
        ]


class PaymentCreateSerializer(PaymentSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "card_number",
            "expiry_month",
            "expiry_year",
            "cvc",
            "borrowing",
        ]


class RefundActionSerializer(PaymentSerializer):
    refund = serializers.ChoiceField(choices=["I want to refund my payment"])

    class Meta:
        model = Payment
        fields = ["refund"]


class FinesSerializer(serializers.ModelSerializer):
    # fines_paid = serializers.DecimalField(max_digits=6, decimal_places=2)
    # stripe_payment_id = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("context").get("request")

        if request.user and "borrowing" in self.fields:
            self.fields["borrowing"].queryset = Borrowing.objects.filter(
                user=request.user, fines_applied__isnull=False, fines_paid=False
            )

    def create(self, validated_data):
        borrowing = validated_data.get("borrowing")

        fines = calculate_fines(borrowing.id)
        if fines:
            response = stripe_card_payment(borrowing.id, calculate_fines)
            validated_data["fines_paid"] = fines
            validated_data["stripe_payment_id"] = response["stripe_payment_id"]
            validated_data["payment"] = borrowing.payment
            print("valdata", borrowing.__dict__)

        return super().create(validated_data)

    class Meta:
        model = Fines
        fields = [
            "id",
            "card_number",
            "expiry_month",
            "expiry_year",
            "cvc",
            "borrowing",
            "payment",
            "fines_paid",
            "stripe_payment_id",
        ]


class FinesListSerializer(FinesSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_user(obj):
        return f"{obj.user.profile.full_name} ({obj.user.email})"

    class Meta:
        model = Fines
        fields = [
            "id",
            "fines_paid",
            "borrowing",
            "user",
            "payment",
            "stripe_payment_id",
        ]


class FinesDetailSerializer(FinesListSerializer):
    borrowing = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Fines
        fields = [
            "id",
            "fines_paid",
            "borrowing",
            "user",
            "payment",
            "stripe_payment_id",
        ]


class FinesCreateSerializer(FinesSerializer):
    class Meta:
        model = Fines
        fields = [
            "id",
            "card_number",
            "expiry_month",
            "expiry_year",
            "cvc",
            "borrowing",
        ]
