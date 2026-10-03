"""Namespaced routes of the clinic setup screens (``scheduling:`` names).

The older scheduling routes keep their flat names (``unit_list``, ...); the setup
screens that feed the patient app use the ``scheduling:`` namespace. They are
mounted from ``scheduling/urls.py``, so they live under ``/agenda/``.
"""

from django.urls import path

from .availability_views import (
    availability_create,
    availability_list,
    availability_preview,
    availability_remove,
    availability_update,
)
from .service_views import (
    service_activate,
    service_create,
    service_deactivate,
    service_list,
    service_update,
)

app_name = "scheduling"

urlpatterns = [
    # Catálogo de serviços (o que o paciente pode pedir no app)
    path("servicos/", service_list, name="service_list"),
    path("servicos/novo/", service_create, name="service_create"),
    path("servicos/<uuid:service_id>/editar/", service_update, name="service_update"),
    path(
        "servicos/<uuid:service_id>/ativar/",
        service_activate,
        name="service_activate",
    ),
    path(
        "servicos/<uuid:service_id>/inativar/",
        service_deactivate,
        name="service_deactivate",
    ),
    # Horários de atendimento por profissional e unidade
    path("disponibilidade/", availability_list, name="availability_list"),
    path("disponibilidade/novo/", availability_create, name="availability_create"),
    path(
        "disponibilidade/previa/",
        availability_preview,
        name="availability_preview",
    ),
    path(
        "disponibilidade/<uuid:pattern_id>/editar/",
        availability_update,
        name="availability_update",
    ),
    path(
        "disponibilidade/<uuid:pattern_id>/remover/",
        availability_remove,
        name="availability_remove",
    ),
]
