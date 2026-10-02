"""Django configuration for the patient mobile API boundary."""

from django.apps import AppConfig


class MobileApiConfig(AppConfig):
    """Configure token sessions for the post-discharge patient app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mobile_api"
    verbose_name = "API do app do paciente"
