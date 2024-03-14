from datetime import date

import telebot
from django.conf import settings
from django.contrib.auth import get_user_model
from celery import shared_task
from django.db import transaction
from django.urls import reverse_lazy

from library.models import Book
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.utils import calculate_fines

from user.models import Profile


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

    for borrowing in overdue_borrowings:
        fines = calculate_fines(borrowing.id)
        if borrowing.fines_applied != fines:
            borrowing.fines_applied = fines
            borrowing.save()


@shared_task
def notify_about_borrowing_create(
    borrowing_id, user_id
) -> int | Exception | str | Response:
    from .models import Borrowing

    try:
        borrowing = Borrowing.objects.get(pk=borrowing_id)
        user = get_user_model().objects.get(pk=user_id)
        borrowing_url = reverse_lazy(
            "borrowings:borrowings-detail", kwargs={"pk": borrowing_id}
        )

        notification_message = (
            f"New borrowing created:\n"
            f"{borrowing.book.title} by {borrowing.book.author}\n"
            f"Please return it by:"
            f" {borrowing.expected_return_date}\n"
            f"View details: {settings.BASE_URL}{borrowing_url}"
        )

        bot = telebot.TeleBot(settings.TELEGRAM["bot_token"])
        profile = Profile.objects.get(user=user)
        chat_id = profile.telegram_chat_id

        if chat_id:
            bot.send_message(chat_id, notification_message)

    except Exception as e:
        return str(e)
