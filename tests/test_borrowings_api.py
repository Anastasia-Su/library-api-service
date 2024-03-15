import tempfile
import os
from datetime import date, timedelta, datetime
from decimal import Decimal

from PIL import Image
from decimal import ROUND_UP
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
)
from tests import test_library_api, test_user_api

from user.models import Profile


BORROWING_URL = reverse("borrowings:borrowings-list")


def detail_url(borrowing_id):
    return reverse("borrowings:borrowings-detail", args=[borrowing_id])


def return_borrowing_url(borrowing_id):
    return reverse("borrowings:borrowings-return-borrowing", args=[borrowing_id])


def payload(i):
    return {
        "borrow_date": "2024-03-26",
        "expected_return_date": "2024-04-18",
        "book": test_library_api.sample_book(i).pk,
        "paid": True,
    }


def sample_user(i):
    user = get_user_model().objects.create_user(
        f"test@test{i}.com",
        "testpass",
    )
    user.profile = Profile.objects.create(user=user)
    return user


def sample_borrowing(i, **params):
    defaults = {
        "borrow_date": "2024-01-26",
        "expected_return_date": "2024-04-18",
        "returned": None,
        "cancelled": False,
        "paid": False,
        "stripe_payment_id": None,
        "fines_applied": None,
        "fines_paid": False,
        "book": test_library_api.sample_book(i),
    }
    defaults.update(params)

    return Borrowing.objects.create(**defaults)


class UnauthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@test.com", "testpass")
        self.profile = Profile.objects.create(user=self.user)

        self.client.force_authenticate(self.user)

    def test_list_unpaid_borrowings_forbidden(self):
        """Users are not allowed to see borrowings before successful payment"""
        sample_borrowing(1, user=self.user)
        sample_borrowing(2, user=self.user)

        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.data, [])

    def test_list_returned_borrowings_forbidden(self):
        """Users are not allowed to see borrowings, they returned"""
        sample_borrowing(1, user=self.user, returned=date.today())
        sample_borrowing(2, user=self.user, returned=date.today())

        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.data, [])

    def test_list_cancelled_borrowings_forbidden(self):
        """Users are not allowed to see borrowings, they cancelled"""
        sample_borrowing(1, user=self.user, cancelled=True)
        sample_borrowing(2, user=self.user, cancelled=True)

        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.data, [])

    def test_see_others_borrowings_forbidden(self):
        """Users are not allowed to see borrowings of other users"""
        borrowing1 = sample_borrowing(1, user=self.user, paid=True)
        borrowing2 = sample_borrowing(2, user=sample_user(2), paid=True)
        borrowing3 = sample_borrowing(3, user=sample_user(3), paid=True)

        res = self.client.get(BORROWING_URL)

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3 = BorrowingListSerializer(borrowing3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_borrow_date_vaildation(self):
        """Borrow date should not be earlier than today"""
        payload_var = payload(1)
        yesterday = date.today() - timedelta(days=1)
        payload_var["borrow_date"] = yesterday.strftime("%Y-%m-%d")

        res = self.client.post(BORROWING_URL, payload_var, follow=True)

        self.assertFalse(res.redirect_chain)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expected_return_date_validation(self):
        """Expected return date should not be earlier than borrow date"""
        payload_var = payload(1)
        borrow_date = datetime.strptime(payload_var["borrow_date"], "%Y-%m-%d").date()
        yesterday = borrow_date - timedelta(days=1)
        payload_var["expected_return_date"] = yesterday.strftime("%Y-%m-%d")

        res = self.client.post(BORROWING_URL, payload_var, follow=True)

        self.assertFalse(res.redirect_chain)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redirect_borrowing_to_payment_page(self):
        """When a user creates borrowing, they should be redirected to payment page"""
        res = self.client.post(BORROWING_URL, payload(1), follow=True)

        self.assertTrue(res.redirect_chain)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_paid_borrowings(self):
        sample_borrowing(1, user=self.user, paid=True)
        sample_borrowing(2, user=self.user, paid=True)

        res = self.client.get(BORROWING_URL)

        borrowings = Borrowing.objects.all()
        serializer = BorrowingListSerializer(borrowings, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_borrowing_detail(self):
        borrowing = sample_borrowing(1, user=self.user, paid=True)
        url = detail_url(borrowing.id)
        res = self.client.get(url)

        serializer = BorrowingDetailSerializer(borrowing)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AdminBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_superuser=True
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client.force_authenticate(self.user)

    def test_list_unpaid_borrowings_allowed(self):
        """Admin should be able to see all borrowings, incl. unpaid, cancelled and returned"""
        sample_borrowing(1, user=self.user)
        sample_borrowing(2, user=self.user)

        res = self.client.get(BORROWING_URL)
        self.assertNotEquals(res.data, [])

    def test_list_returned_borrowings_allowed(self):
        """Admin should be able to see all borrowings, incl. unpaid, cancelled and returned"""
        sample_borrowing(1, user=self.user, returned=date.today())
        sample_borrowing(2, user=self.user, returned=date.today())

        res = self.client.get(BORROWING_URL)
        self.assertNotEquals(res.data, [])

    def test_list_cancelled_borrowings_allowed(self):
        """Admin should be able to see all borrowings, incl. unpaid, cancelled and returned"""
        sample_borrowing(1, user=self.user, cancelled=True)
        sample_borrowing(2, user=self.user, cancelled=True)

        res = self.client.get(BORROWING_URL)
        self.assertNotEquals(res.data, [])

    def test_filter_borrowings_by_user_id(self):
        borrowing1 = sample_borrowing(1, user=self.user)
        borrowing2 = sample_borrowing(2, user=sample_user(2))
        borrowing3 = sample_borrowing(3, user=sample_user(3))

        res = self.client.get(BORROWING_URL, {"user": 2})

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3 = BorrowingListSerializer(borrowing3)

        self.assertNotIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_borrowings_by_returned_status(self):
        borrowing1 = sample_borrowing(1, user=self.user, returned=date.today())
        borrowing2 = sample_borrowing(2, user=sample_user(2), returned=None)
        borrowing3 = sample_borrowing(3, user=sample_user(3), returned=None)

        res1 = self.client.get(BORROWING_URL, {"returned": "true"})
        res2 = self.client.get(BORROWING_URL, {"returned": "false"})

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3 = BorrowingListSerializer(borrowing3)

        self.assertIn(serializer1.data, res1.data)
        self.assertNotIn(serializer2.data, res1.data)
        self.assertNotIn(serializer3.data, res1.data)

        self.assertNotIn(serializer1.data, res2.data)
        self.assertIn(serializer2.data, res2.data)
        self.assertIn(serializer3.data, res2.data)

    def test_filter_borrowings_by_fines_applied(self):
        borrowing1 = sample_borrowing(1, user=self.user, fines_applied=2.5)
        borrowing2 = sample_borrowing(2, user=sample_user(2), fines_applied=None)
        borrowing3 = sample_borrowing(3, user=sample_user(3), fines_applied=None)

        res1 = self.client.get(BORROWING_URL, {"fines": "true"})
        res2 = self.client.get(BORROWING_URL, {"fines": "false"})

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3 = BorrowingListSerializer(borrowing3)

        self.assertIn(serializer1.data, res1.data)
        self.assertNotIn(serializer2.data, res1.data)
        self.assertNotIn(serializer3.data, res1.data)

        self.assertNotIn(serializer1.data, res2.data)
        self.assertIn(serializer2.data, res2.data)
        self.assertIn(serializer3.data, res2.data)


class BorrowingReturnTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@test.com", "testpass")
        self.profile = Profile.objects.create(user=self.user)

        self.client.force_authenticate(self.user)

    def test_return_borrowing_book_inventory_incremented(self):
        borrowing = sample_borrowing(1, user=self.user, paid=True)
        url = return_borrowing_url(borrowing.id)
        self.assertIsNone(borrowing.returned)

        initial_book_inventory = borrowing.book.inventory

        res = self.client.post(url, {"to_return": "I return it"})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        borrowing.refresh_from_db()

        self.assertEqual(borrowing.returned, date.today())
        self.assertEqual(borrowing.book.inventory, initial_book_inventory + 1)

    def test_already_returned_borrowing(self):
        borrowing = sample_borrowing(
            1, user=self.user, paid=True, returned=date.today()
        )
        initial_book_inventory = borrowing.book.inventory
        url = return_borrowing_url(borrowing.id)

        response = self.client.post(url, {"to_return": "I return it"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(borrowing.book.inventory, initial_book_inventory)
