import random
from datetime import date

import telebot
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from borrowings.models import Borrowing
from telebot import types


class TelegramBot:
    def __init__(self):
        self.bot = telebot.TeleBot(settings.TELEGRAM["bot_token"])
        self.user_email = None
        self.verification_codes = {}

        @self.bot.message_handler(commands=["start", "help"])
        def send_welcome(message):
            self.bot.reply_to(message, "Please enter your email.")

        @self.bot.callback_query_handler(
            func=lambda call: call.data in ["check_last", "check_overdue"]
        )
        def process_message(call):
            chat_id = call.message.chat.id

            if self.user_email:
                if call.data == "check_last":
                    last_borrowing = (
                        Borrowing.objects.filter(user__email=self.user_email)
                        .order_by("id")
                        .last()
                    )

                    book_instance = last_borrowing.book
                    notification_message = (
                        f"New borrowing created:\n"
                        f"{book_instance.title} by {book_instance.author}\n"
                        f"Please return it by:"
                        f" {last_borrowing.expected_return_date}"
                    )
                    self.bot.send_message(chat_id, notification_message)

                if call.data == "check_overdue":
                    overdue_borrowings = Borrowing.objects.filter(
                        user__email=self.user_email,
                        expected_return_date__lt=date.today(),
                    ).order_by("expected_return_date")

                    for borrowing in overdue_borrowings:
                        book_instance = borrowing.book
                        notification_message = (
                            f"{book_instance.title} by {book_instance.author}\n"
                            f"Should have been returned by:"
                            f" {borrowing.expected_return_date}"
                        )
                        self.bot.send_message(chat_id, notification_message)
            else:
                self.bot.send_message(chat_id, "Please enter your email.")

        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            chat_id = message.chat.id

            if message.text.isdigit() and self.user_email:
                if message.text == self.verification_codes.get(self.user_email):
                    self.bot.send_message(chat_id, "Verification successful!")

                    markup = types.InlineKeyboardMarkup()
                    check_last = types.InlineKeyboardButton(
                        "Check my last borrowing", callback_data="check_last"
                    )
                    check_overdue = types.InlineKeyboardButton(
                        "Check my overdue borrowings", callback_data="check_overdue"
                    )
                    markup.add(check_last, check_overdue)

                    self.bot.send_message(
                        chat_id, "What do you want to do?", reply_markup=markup
                    )
                else:
                    self.bot.send_message(
                        chat_id, "Verification code incorrect. Please try again."
                    )
            elif self.email_exists_in_database(message.text):
                verification_code = self.generate_verification_code()
                send_mail(
                    "Verification Code",
                    f"Your verification code is: {verification_code}",
                    settings.EMAIL_HOST_USER,
                    [message.text],
                    fail_silently=False,
                )
                self.bot.send_message(
                    chat_id,
                    f"A verification code has been sent to {message.text}. Please enter the code here.",
                )

                self.user_email = message.text
                self.verification_codes[message.text] = verification_code
            else:
                self.bot.reply_to(message, "Your email does not exist in our database")

    @staticmethod
    def email_exists_in_database(email):
        return get_user_model().objects.filter(email=email).exists()

    @staticmethod
    def generate_verification_code():
        return "".join(random.choices("0123456789", k=6))

    def start_polling(self):
        self.bot.infinity_polling(interval=0, timeout=20)


telegram_bot = TelegramBot()


class Command(BaseCommand):
    def handle(self, *args, **options):
        telegram_bot.start_polling()
