from datetime import date

import stripe
from decimal import Decimal
from django.conf import settings
from rest_framework import status

from .models import Borrowing


def calculate_amount(borrowing_id):
    borrowing = Borrowing.objects.get(pk=borrowing_id)
    duration = borrowing.expected_return_date - borrowing.borrow_date
    if duration.days:
        amount_dollars = borrowing.book.daily_fee * duration.days
    else:
        amount_dollars = borrowing.book.daily_fee

    return amount_dollars


def calculate_fines(borrowing_id):
    fine_multiplier = Decimal(1.2)
    borrowing = Borrowing.objects.get(pk=borrowing_id)

    duration = date.today() - borrowing.expected_return_date
    # duration = borrowing.returned - borrowing.expected_return_date
    if duration.days > 0:
        amount_dollars = borrowing.book.daily_fee * duration.days * fine_multiplier
    else:
        amount_dollars = 0

    return amount_dollars


def stripe_card_payment(borrowing_id, func):
    try:
        amount_dollars = func(borrowing_id)
        amount = int(amount_dollars * 100)
        currency = "usd"

        payment_intent = create_payment_intent(amount, currency)
        stripe_payment_id = payment_intent.id

        success, message = handle_payment_response(payment_intent)
        if success:
            return {
                "message": message,
                "status": status.HTTP_200_OK,
                "stripe_payment_id": stripe_payment_id,
            }
        else:
            return {"error": message, "status": status.HTTP_400_BAD_REQUEST}
    except Exception as e:
        return {"error": str(e), "status": status.HTTP_400_BAD_REQUEST}


def create_payment_intent(amount, currency):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payment_intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        payment_method_types=["card"],
        payment_method=settings.STRIPE_PAYMENT_METHOD,
        confirm=True,
    )

    return payment_intent


def handle_payment_response(payment_intent):
    if payment_intent.status == "succeeded":
        return True, "Payment succeeded"
    else:
        error_message = (
            payment_intent.last_payment_error
            and payment_intent.last_payment_error.message
        )
        return False, f"Payment failed: {error_message}"
