import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


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


def profile_picture_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.last_name)}-{uuid.uuid4()}{extension}"

    return os.path.join("uploads/profile/", filename)


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        on_delete=models.CASCADE,
        null=True,
        unique=True,
    )

    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    image = models.ImageField(
        null=True, blank=True, upload_to=profile_picture_file_path
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({get_user_model().email})"

    class Meta:
        ordering = ["id", "last_name"]
