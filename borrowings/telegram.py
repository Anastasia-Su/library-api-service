import requests
from django.conf import settings

from library.models import Book


def send_notification(borrowing_data):
    bot_token = settings.TELEGRAM["bot_token"]
    update_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    response = requests.get(update_url).json()
    chat_id = response["result"][0]["message"]["chat"]["id"]

    book_id = borrowing_data.get("book")
    book_instance = Book.objects.get(pk=book_id)

    notification_message = (
        f"New borrowing created:\n"
        f"{book_instance.title} by {book_instance.author}\n"
        f"Please return it by:"
        f" {borrowing_data.get('expected_return_date')}"
    )

    params = {"chat_id": chat_id, "text": notification_message}

    response = requests.post(send_url, params=params)
    return response.json()
