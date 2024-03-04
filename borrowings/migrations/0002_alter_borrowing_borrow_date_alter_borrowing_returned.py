# Generated by Django 5.0.2 on 2024-02-23 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("borrowings", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="borrowing",
            name="borrow_date",
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name="borrowing",
            name="returned",
            field=models.DateField(blank=True, null=True),
        ),
    ]