"""Django configuration for the concierge domain."""

from django.apps import AppConfig


class ConciergeConfig(AppConfig):
    """Configure the concierge and post-discharge follow-up boundary."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "concierge"
    verbose_name = "Concierge e acompanhamento pós-alta"
