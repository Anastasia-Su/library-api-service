import time

import telebot
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand

from borrowings.models import Borrowing


class TelegramBot:
    def __init__(self):
        self.bot = telebot.TeleBot(settings.TELEGRAM["bot_token"])
        self.user_email = None

        @self.bot.message_handler(commands=["start", "help"])
        def send_welcome(message):
            self.bot.reply_to(message, "Please enter your email.")

        @self.bot.message_handler(commands=["check"])
        def process_message(message):
            chat_id = message.chat.id

            if self.user_email:
                last_borrowing = Borrowing.objects.filter(
                    user__email=self.user_email
                ).order_by("id").last()
                book_instance = last_borrowing.book

                notification_message = (
                    f"New borrowing created:\n"
                    f"{book_instance.title} by {book_instance.author}\n"
                    f"Please return it by:"
                    f" {last_borrowing.expected_return_date}"
                )
                self.bot.send_message(chat_id, notification_message)
            else:
                self.bot.send_message(chat_id, "Please enter your email.")

        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            if self.email_exists_in_database(message.text):
                self.bot.reply_to(message, "Exists")
                # session = SessionStore()
                # session["user_email"] = message.text
                # session.save()

                self.user_email = message.text
            else:
                self.bot.reply_to(message, "Your email does not exist in our database")

    @staticmethod
    def email_exists_in_database(email):
        return get_user_model().objects.filter(email=email).exists()

    def start_polling(self):
        self.bot.infinity_polling(interval=0, timeout=20)


telegram_bot = TelegramBot()


class Command(BaseCommand):
    def handle(self, *args, **options):
        telegram_bot.start_polling()


