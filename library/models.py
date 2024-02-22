from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=3, decimal_places=2)

    COVER_CHOICES = [
        ("H", "Hard"),
        ("S", "Soft"),
    ]
    cover = models.CharField(max_length=1, choices=COVER_CHOICES, blank=True)

    def __str__(self):
        return f"{self.title} ({self.author})"

    class Meta:
        ordering = ["author", "title"]
