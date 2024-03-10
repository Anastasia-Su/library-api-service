from django.conf import settings
from django.db import models
from library.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    returned = models.DateField(null=True, blank=True)
    cancelled = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    stripe_payment_id = models.CharField(max_length=255, null=True)
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrowings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return (
            f"{self.book}:\nfrom {self.borrow_date}" f" to {self.expected_return_date}"
        )

    class Meta:
        ordering = ["id", "expected_return_date", "book"]


class Payment(models.Model):
    card_number = models.IntegerField()
    expiry_month = models.IntegerField()
    expiry_year = models.IntegerField()
    cvc = models.IntegerField()
    amount_paid = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
    )
    stripe_payment_id = models.CharField(max_length=255, null=True)
    refunded = models.BooleanField(default=False)
    borrowing = models.ForeignKey(
        Borrowing, on_delete=models.PROTECT, related_name="payments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return f"{self.card_number}\n{self.expiry_year}/{self.expiry_month}"
