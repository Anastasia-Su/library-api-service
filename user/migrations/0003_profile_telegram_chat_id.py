# Generated by Django 5.0.2 on 2024-03-14 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0002_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="telegram_chat_id",
            field=models.CharField(max_length=255, null=True),
        ),
    ]