import json

import requests
import uuid
from datetime import date

from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.utils import timezone

import telebot
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Borrowing
from .serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    ReturnActionSerializer,
    BorrowingReadonlySerializer,
)
from library.permissions import IsAuthenticatedReadOnly, IsCurrentlyLoggedIn

from library.models import Book

from user.management.commands.start_bot import telegram_bot

import logging

logger = logging.getLogger(__name__)

bot_token = settings.TELEGRAM["bot_token"]
TELEGRAM_API_URL = f"https://api.telegram.org/bot{bot_token}/"
NGROK = "https://9673-178-150-12-234.ngrok-free.app/"


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if not self.request.user.is_authenticated:
            return BorrowingReadonlySerializer
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        if self.action == "return_borrowing":
            return ReturnActionSerializer
        return BorrowingSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "return_borrowing"]:
            return [IsCurrentlyLoggedIn()]
        if self.action == "destroy":
            return [IsAdminUser()]

        return [IsAuthenticated()]

    @staticmethod
    def generate_session_key():
        return str(uuid.uuid4())

    def create(self, request, *args, **kwargs):
        book_id = request.data.get("book")
        book_instance = Book.objects.get(pk=book_id)

        if book_instance.inventory > 0:
            book_instance.inventory -= 1
            book_instance.save()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            session_key = self.generate_session_key()
            session = SessionStore(session_key=session_key)
            session["borrowing_data"] = serializer.data
            print(session["borrowing_data"])

            session.save()

            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

        return Response(
            {"error": "This book is not currently available"},
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        methods=["POST"],
        detail=True,
        url_path="return-borrowing",
    )
    def return_borrowing(self, request, pk):
        """Endpoint for returning a borrowing"""
        borrowing = self.get_object()

        if request.method == "POST":
            if borrowing.returned is not None:
                return Response(
                    {"error": "This book is already returned"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            borrowing.returned = date.today()

            serializer = self.get_serializer(borrowing, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            book_id = borrowing.book.id
            book_instance = Book.objects.get(pk=book_id)

            book_instance.inventory += 1
            book_instance.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response({"error": "Fail"}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        user = self.request.query_params.get("user")
        is_active = self.request.query_params.get("is_active")
        queryset = self.queryset

        if user:
            user_id = int(user)
            queryset = queryset.filter(user__id=user_id)

        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(returned__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(returned__isnull=False)
            else:
                return Borrowing.objects.none()

        return queryset


# telegram_bot = telebot.TeleBot(settings.TELEGRAM["bot_token"])

#
# @csrf_exempt
# def telegram_bot(request):
#   if request.method == 'POST':
#     message = json.loads(request.body.decode('utf-8'))
#     chat_id = message['message']['chat']['id']
#     text = message['message']['text']
#     send_message("sendMessage", {
#       'chat_id': f'your message {text}'
#     })
#   return HttpResponse('ok')
#
#
# def send_message(method, data):
#     return requests.post(TELEGRAM_API_URL + method, data)
#
#
# @csrf_exempt
# def telegram_webhook(request):
#     # if request.method == 'POST':
#     #     try:
#     #         update = telebot.types.Update.de_json(request.body)
#     #         telegram_bot.bot.process_new_updates([update])
#     #         logger.info("Update processed successfully")
#     #     except Exception as e:
#     #         logger.error("Error processing update: %s", str(e))
#     #         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
#
#     response = requests.post(TELEGRAM_API_URL + "setWebhook?url=" + NGROK).json()
#
#     return HttpResponse(f"{response}")


# def setwebhook(request):
#     response = requests.post(TELEGRAM_API_URL + "setWebhook?url=" + NGROK).json()
#     return HttpResponse(f"{response}")
#
#
# @csrf_exempt
# def telegram_bot(request):
#     if request.method == "POST":
#         update = json.loads(request.body.decode("utf-8"))
#         handle_update(update)
#         return HttpResponse("ok")
#     else:
#         return HttpResponseBadRequest("Bad Request")
#
#
# def handle_update(update):
#     chat_id = update["message"]["chat"]["id"]
#     text = update["message"]["text"]
#     send_message("sendMessage", {"chat_id": chat_id, "text": f"you said {text}"})
#
#
# def send_message(method, data):
#     return requests.post(TELEGRAM_API_URL + method, data)


def set_webhook():
    response = requests.get(f'{TELEGRAM_API_URL}/setWebhook?url={NGROK}')
    if response.status_code == 200:
        print('Webhook set successfully!')
    else:
        print('Failed to set webhook:', response.text)


set_webhook()


def send_message(chat_id, text):
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    # telegram_bot.bot.send_message(chat_id, text)

    return requests.post(
        f'{TELEGRAM_API_URL}/sendMessage',
        json=payload
    )

    # if response.status_code != 200:
    #     print(f"Failed to send message. Status code: {response.status_code}")




@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        update = json.loads(request.body.decode('utf-8'))
        print("upd_obj", update)
        process_update(update)
        return JsonResponse({'status': 'ok'})
    elif request.method == 'GET':
        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Method Not Allowed'}, status=405)


def process_update(update):
    chat_id = update['message']['chat']['id']
    text = update['message']['text']
    print('textaa', text)

    send_message(chat_id, 'Welcome! Please enter your email address:')
