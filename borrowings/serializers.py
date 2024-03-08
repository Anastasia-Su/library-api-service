from datetime import date

from rest_framework import serializers

from .models import Borrowing, Payment


class BorrowingSerializer(serializers.ModelSerializer):

    @staticmethod
    def validate_borrow_date(value):
        if value < date.today():
            raise serializers.ValidationError(
                "Borrow date cannot be earlier than today."
            )
        return value

    @staticmethod
    def validate_expected_return_date(value):
        if value < date.today():
            raise serializers.ValidationError(
                "Expected return date cannot be earlier than today."
            )
        return value

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "book",
            "borrow_date",
            "expected_return_date"
        ]


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
        fields = ["id", "user", "book", "borrowed", "paid", "returned"]


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
            "returned",
        ]


class ReturnActionSerializer(BorrowingSerializer):
    to_return = serializers.ChoiceField(choices=["I return it"])

    class Meta:
        model = Borrowing
        fields = ["to_return"]


class PaymentSerializer(serializers.ModelSerializer):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     request = kwargs["context"]["request"]
    #
    #     if request.user:
    #         self.fields["borrowing"].queryset = Borrowing.objects.filter(
    #             user=request.user,
    #             paid=False
    #         )

    #
    # @staticmethod
    # def validate_expiry_month(value):
    #     if not 1 <= int(value) <= 12:
    #         raise serializers.ValidationError("Invalid expiry month.")
    #
    # @staticmethod
    # def validate_expiry_year(value):
    #     today = datetime.now()
    #     if not int(value) >= today.year:
    #         raise serializers.ValidationError("Invalid expiry year.")
    #
    # @staticmethod
    # def validate_cvc(value):
    #     if len(str(value)) not in [3, 4]:
    #         raise serializers.ValidationError("Invalid cvc number.")

    class Meta:
        model = Payment
        fields = [
            "id",
            "card_number",
            "expiry_month",
            "expiry_year",
            "cvc",
            # "borrowing",
        ]


class PaymentListSerializer(PaymentSerializer):
    expiry = serializers.SerializerMethodField(read_only=True)

    def get_expiry(self, obj):
        return f"{obj.expiry_year}/{obj.expiry_month}"

    class Meta:
        model = Payment
        fields = [
            "id",
            "card_number",
            "expiry",
            "cvc",
            "borrowing",
        ]


class PaymentDetailSerializer(PaymentListSerializer):
    borrowing = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "card_number",
            "expiry",
            "cvc",
            "borrowing",
        ]
