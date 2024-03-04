import time

import telebot
import threading
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management.base import BaseCommand
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from library.models import Book


class TelegramBot:
    def __init__(self):
        self.bot = telebot.TeleBot(settings.TELEGRAM["bot_token"])

        @self.bot.message_handler(commands=["start", "help"])
        def send_welcome(message):
            self.bot.reply_to(message, "Please enter your email.")

        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            if self.email_exists_in_database(message.text):
                self.bot.reply_to(message, "Exists")
                session = SessionStore()
                session["user_email"] = message.text
                session.save()
            else:
                self.bot.reply_to(message, "Your email does not exist in our database")

    @staticmethod
    def email_exists_in_database(email):
        return get_user_model().objects.filter(email=email).exists()

    def start_polling(self):
        self.bot.infinity_polling(interval=0, timeout=20)

    # @staticmethod
    # def send_notification(borrowing_data):
    #     bot_token = settings.TELEGRAM["bot_token"]
    #     update_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    #     send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    #
    #     response = requests.get(update_url).json()
    #
    #     if "result" in response and len(response["result"]):
    #
    #         chat_id = response["result"][-1]["message"]["chat"]["id"]
    #
    #         book_id = borrowing_data.get("book")
    #         book_instance = Book.objects.get(pk=book_id)
    #
    #         notification_message = (
    #             f"New borrowing created:\n"
    #             f"{book_instance.title} by {book_instance.author}\n"
    #             f"Please return it by:"
    #             f" {borrowing_data.get('expected_return_date')}"
    #         )
    #
    #         params = {"chat_id": chat_id, "text": notification_message}
    #
    #         response = requests.post(send_url, params=params)
    #         return response.json()
    #
    # def check_and_send_notifications(self):
    #     while True:
    #         sessions = Session.objects.all()
    #         for session in sessions:
    #             if session:
    #                 borrowing_data = session.get_decoded().get('borrowing_data')
    #                 if borrowing_data:
    #                     self.send_notification(borrowing_data)
    #         time.sleep(10)


telegram_bot = TelegramBot()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # telegram_bot.start_polling()
        telegram_bot.bot.set_webhook(
            url="https://9673-178-150-12-234.ngrok-free.app"
        )

        call_command('runserver', '0.0.0.0:8000')


    # @staticmethod
    # def send_notification():
    #     bot_token = settings.TELEGRAM["bot_token"]
    #     update_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    #     send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    #
    #     response = requests.get(update_url).json()
    #
    #     if response["result"]:
    #         chat_id = response["result"][-1]["message"]["chat"]["id"]
    #
    #         session = Session.objects.last()
    #
    #         borrowing_data = session.get_decoded().get('borrowing_data')
    #         print("bdata", borrowing_data)
    #
    #         if borrowing_data:
    #             book_id = borrowing_data.get("book")
    #             book_instance = Book.objects.get(pk=book_id)
    #
    #             notification_message = (
    #                 f"New borrowing created:\n"
    #                 f"{book_instance.title} by {book_instance.author}\n"
    #                 f"Please return it by:"
    #                 f" {borrowing_data.get('expected_return_date')}"
    #             )
    #             # self.bot.reply_to(message, notification_message)
    #         params = {"chat_id": chat_id, "text": notification_message}
    #
    #         response = requests.post(send_url, params=params)
    #         return response.json()



    # @staticmethod
    # def send_notification(borrowing_data):
    #     bot_token = settings.TELEGRAM["bot_token"]
    #     update_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    #     send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    #
    #     response = requests.get(update_url).json()
    #
    #     if response["result"]:
    #         chat_id = response["result"][-1]["message"]["chat"]["id"]
    #
    #         book_id = borrowing_data.get("book")
    #         book_instance = Book.objects.get(pk=book_id)
    #
    #         notification_message = (
    #             f"New borrowing created:\n"
    #             f"{book_instance.title} by {book_instance.author}\n"
    #             f"Please return it by:"
    #             f" {borrowing_data.get('expected_return_date')}"
    #         )
    #
    #         params = {"chat_id": chat_id, "text": notification_message}
    #
    #         response = requests.post(send_url, params=params)
    #         return response.json()




