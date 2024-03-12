# Generated by Django 5.0.2 on 2024-03-11 16:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("borrowings", "0016_borrowing_cancelled_payment_refunded"),
    ]

    operations = [
        migrations.AddField(
            model_name="borrowing",
            name="fines",
            field=models.DecimalField(decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="fines",
            field=models.DecimalField(decimal_places=2, max_digits=6, null=True),
        ),
    ]