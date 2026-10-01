# apps/super_admin/management/commands/setup_super_admin.py
import os
import getpass

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.super_admin.models import AdminUser


class Command(BaseCommand):
    help = "Create or promote a super admin (accounts.User + AdminUser)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=os.environ.get("SUPER_ADMIN_EMAIL"))
        parser.add_argument("--password", default=os.environ.get("SUPER_ADMIN_PASSWORD"))
        parser.add_argument("--noinput", action="store_true")

    def handle(self, *args, **options):
        User = get_user_model()

        email = (options["email"] or "").strip()
        password = options["password"]
        noinput = options["noinput"]

        if not email:
            if noinput:
                raise CommandError("Missing email and --noinput was set.")
            email = input("Enter super admin email: ").strip()
        if not email:
            raise CommandError("Email is required.")

        if not password:
            if noinput:
                raise CommandError("Missing password and --noinput was set.")
            password = getpass.getpass("Enter super admin password: ")
            if password != getpass.getpass("Confirm password: "):
                raise CommandError("Passwords do not match.")

        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError("Password rejected: " + "; ".join(e.messages))

        with transaction.atomic():
            # accounts.User — keyed on email, matching AdminUser.__str__ usage.
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"username": email},
            )

            # Enforce auth flags regardless of whether the user was just created.
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save(update_fields=["is_staff", "is_superuser", "password"])

            # OneToOneField → key on user, not email.
            admin, admin_created = AdminUser.objects.update_or_create(
                user=user,
                defaults={
                    "role": AdminUser.Roles.SUPER_ADMIN,
                    "permissions": {"all": True},
                },
            )

        verb = "created" if created else "updated"
        admin_verb = "created" if admin_created else "updated"
        self.stdout.write(self.style.SUCCESS(
            f"User {email} {verb}; AdminUser {admin_verb} with role "
            f"{admin.get_role_display()}."
        ))
