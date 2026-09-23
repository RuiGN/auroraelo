"""Ensure the configured production Master operator exists safely."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User


class Command(BaseCommand):
    """Create the global operator once and validate it on later startups."""

    help = "Ensure the configured Master operator exists without resetting credentials."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create a missing operator or fail closed for an invalid account."""
        email = self._required_setting("MASTER_USER_EMAIL")
        password = self._required_setting("MASTER_USER_PASSWORD")
        canonical_email = email.strip().casefold()

        with transaction.atomic():
            user = (
                User.objects.select_for_update().filter(email=canonical_email).first()
            )
            if user is None:
                User.objects.create_superuser(
                    email=canonical_email,
                    password=password,
                    first_name="Master",
                    last_name="Admin",
                )
                self.stdout.write(self.style.SUCCESS("Master operator created."))
                return

            if not (user.is_active and user.is_staff and user.is_superuser):
                raise CommandError(
                    "Configured Master account is not a valid global operator."
                )

        self.stdout.write("Master operator already valid.")

    @staticmethod
    def _required_setting(name: str) -> str:
        """Return a non-empty setting without ever exposing its value."""
        value = getattr(settings, name, None)
        if not isinstance(value, str) or not value.strip():
            raise CommandError(f"Mandatory Master setting {name} is not configured.")
        return value
