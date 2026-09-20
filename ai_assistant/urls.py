"""Rotas isoladas; inclusão no projeto pertence à integração principal."""

from django.urls import path

from .recovery_views import recovery_assistant, recovery_library

urlpatterns = [
    path("api/v1/recovery/library/", recovery_library, name="recovery-library"),
    path("api/v1/recovery/assistant/", recovery_assistant, name="recovery-assistant"),
]
