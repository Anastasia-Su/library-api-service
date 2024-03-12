from rest_framework import serializers
from .models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "cover", "inventory", "daily_fee"]


class BookListSerializer(BookSerializer):
    book = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_book(obj):
        return f"{obj.title} by {obj.author}"

    class Meta:
        model = Book
        fields = ["id", "book", "cover", "inventory", "daily_fee"]


class BookDetailSerializer(BookSerializer):
    pass
