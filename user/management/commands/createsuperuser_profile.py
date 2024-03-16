from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from user.models import Profile


class Command(createsuperuser.Command):
    help = "Create a superuser account with a profile"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--first-name",
            dest="first_name",
            default="",
            help="Specifies the first name for the superuser.",
        )
        parser.add_argument(
            "--last-name",
            dest="last_name",
            default="",
            help="Specifies the last name for the superuser.",
        )
        parser.add_argument(
            "--bio",
            dest="bio",
            default="",
            help="Specifies the bio for the superuser profile.",
        )

    def handle(self, *args, **options):
        email = options.get("email")
        password = options.get("password")
        first_name = options.get("first_name")
        last_name = options.get("last_name")
        bio = options.get("bio")

        if not email:
            email = input("Enter email: ")
        if not password:
            password = input("Enter password: ")
        if not first_name:
            first_name = input("Enter first_name: ")
        if not last_name:
            last_name = input("Enter last_name: ")
        if not bio:
            bio = input("Enter bio: ")

        profile_data = {
            "first_name": first_name,
            "last_name": last_name,
            "bio": bio,
        }

        try:
            superuser = (
                get_user_model()
                ._default_manager.db_manager()
                .create_superuser(email=email, password=password, **profile_data)
            )
            Profile.objects.create(user=superuser, **profile_data)
        except ValidationError as e:
            raise CommandError("; ".join(e.messages))

        self.stdout.write(
            self.style.SUCCESS(f"Superuser '{email}' created successfully.")
        )
