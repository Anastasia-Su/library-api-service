# Generated by Django 5.0.2 on 2024-03-10 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("borrowings", "0013_borrowing_stripe_payment_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="refund",
            field=models.BooleanField(default=False),
        ),
    ]
