import tempfile
import os
from decimal import Decimal

from PIL import Image
from decimal import ROUND_UP
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from library.models import Book
from library.serializers import BookSerializer, BookListSerializer, BookDetailSerializer

BOOK_URL = reverse("library:books-list")


def payload():
    return {
        "title": f"Sample book",
        "author": f"Sample author",
        "inventory": 10,
        "daily_fee": Decimal(2.8).quantize(Decimal(".01"), rounding=ROUND_UP),
        "cover": "H",
    }


def sample_book(i, **params):
    defaults = {
        "title": f"Sample book{i}",
        "author": f"Sample author{i}",
        "inventory": 10,
        "daily_fee": 2.8,
        "cover": "H",
    }
    defaults.update(params)

    return Book.objects.create(**defaults)


# def sample_journey(i, **params):
#     station1 = Station.objects.create(name=f"ST{i}", latitude=1.1, longitude=6.8)
#     station2 = Station.objects.create(name=f"ST{i + 1}", latitude=9.1, longitude=56.8)
#     route = Route.objects.create(source=station1, destination=station2)
#
#     defaults = {
#         "departure_time": "2024-01-11 14:00:00",
#         "arrival_time": "2024-01-12 06:00:00",
#         "book": sample_book(i),
#         "route": route,
#     }
#     defaults.update(params)
#
#     return Journey.objects.create(**defaults)


# def image_upload_url(profile_id):
#     """Return URL for recipe image upload"""
#     return reverse("station:book-upload-image", args=[book_id])


def detail_url(book_id):
    return reverse("library:books-detail", args=[book_id])


class UnauthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(BOOK_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_books(self):
        sample_book(1)
        sample_book(2)

        res = self.client.get(BOOK_URL)

        books = Book.objects.all()
        serializer = BookListSerializer(books, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_books_by_title(self):
        book1 = sample_book(3, title="name1")
        book2 = sample_book(4, title="name2")
        book3 = sample_book(5, title="another")

        res = self.client.get(BOOK_URL, {"title": "name"})

        serializer1 = BookListSerializer(book1)
        serializer2 = BookListSerializer(book2)
        serializer3 = BookListSerializer(book3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_book_detail(self):
        book = sample_book(6)
        url = detail_url(book.id)
        res = self.client.get(url)

        serializer = BookDetailSerializer(book)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_book_forbidden(self):
        res = self.client.post(BOOK_URL, payload())

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_book(self):
        payload_var = payload()
        res = self.client.post(BOOK_URL, payload_var)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        book = Book.objects.get(id=res.data["id"])
        for key in payload_var:
            self.assertEqual(payload_var[key], getattr(book, key))
