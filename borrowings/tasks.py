from datetime import date

from django.contrib.auth import get_user_model
from celery import shared_task
from django.db import transaction

from library.models import Book
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.utils import calculate_fines


@shared_task
def delay_borrowing_create(
    user_id, book_id, serializer_data
) -> int | Exception | str | Response:
    from .models import Borrowing

    try:
        with transaction.atomic():
            book = Book.objects.get(pk=book_id)

            user = get_user_model().objects.get(pk=user_id)

            borrowing = Borrowing.objects.create(
                user=user,
                book=book,
                borrow_date=serializer_data["borrow_date"],
                expected_return_date=serializer_data["expected_return_date"],
            )
            borrowing.save()

    except Exception as e:
        return str(e)


@shared_task
def calculate_fines_daily():
    overdue_borrowings = Borrowing.objects.filter(
        expected_return_date__lt=date.today(), returned__isnull=True
    )
    print(overdue_borrowings)

    for borrowing in overdue_borrowings:
        fines = calculate_fines(borrowing.id)
        if borrowing.fines_applied != fines:
            borrowing.fines_applied = fines
            borrowing.save()
