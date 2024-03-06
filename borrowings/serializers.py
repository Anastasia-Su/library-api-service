from datetime import date

from rest_framework import serializers

from .models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    @staticmethod
    def validate_borrow_date(value):
        if value < date.today():
            raise serializers.ValidationError("Borrow date cannot be earlier than today.")
        return value

    @staticmethod
    def validate_expected_return_date(value):
        if value < date.today():
            raise serializers.ValidationError("Expected return date cannot be earlier than today.")
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
        fields = ["id", "user", "book", "borrowed", "returned"]


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
            "returned",
        ]


class ReturnActionSerializer(BorrowingSerializer):
    to_return = serializers.ChoiceField(choices=["I return it"])

    class Meta:
        model = Borrowing
        fields = ["to_return"]
