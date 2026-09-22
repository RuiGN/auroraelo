"""Master control panel application configuration."""

from django.apps import AppConfig


class MasterPanelConfig(AppConfig):
    name = "master_panel"
    verbose_name = "Painel Master"
    default_auto_field = "django.db.models.BigAutoField"
