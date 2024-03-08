from django.conf import settings
from django.db import models
from library.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    returned = models.DateField(null=True, blank=True)
    paid = models.BooleanField(default=False)
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="borrowings"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return (
            f"{self.book}:\nfrom {self.borrow_date}"
            f" to {self.expected_return_date}"
        )
    #
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     with transaction.atomic():
    #         borrowing_data = {
    #             "borrow_date": self.borrow_date,
    #             "expected_return_date": self.expected_return_date,
    #             "book_id": self.book_id,
    #             "user_id": self.user_id,
    #             "paid": self.paid,
    #         }
    #         create_after_payment.apply_async(
    #             args=[borrowing_data],
    #             countdown=30
    #         )

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

