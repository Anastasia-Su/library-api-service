from django.conf import settings
from django.db import models
from library.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    returned = models.DateField(null=True, blank=True)
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="borrowings"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.book}: borrowed on {self.borrow_date}"

    class Meta:
        ordering = ["expected_return_date", "book"]


class Payment(models.Model):
    card_number = models.IntegerField()
    expiry_month = models.IntegerField()
    expiry_year = models.IntegerField()
    cvc = models.IntegerField()
    borrowing = models.ForeignKey(
        Borrowing,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.card_number}\n{self.expiry_year}/{self.expiry_month}"

