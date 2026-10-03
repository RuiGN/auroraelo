"""URL routes for the scheduling domain."""

from django.urls import include, path

from .unit_views import (
    room_create,
    room_deactivate,
    unit_create,
    unit_deactivate,
    unit_list,
    unit_update,
)
from .views import (
    appointment_calendar,
    appointment_cancel,
    appointment_complete,
    appointment_confirm,
    appointment_list,
    appointment_no_show,
    appointment_reschedule,
)
from .waitlist_views import (
    waitlist_add,
    waitlist_cancel,
    waitlist_fill,
    waitlist_list,
)

urlpatterns = [
    # Agenda / appointments (8.8.1 & 8.8.2)
    path("", appointment_list, name="appointment_list"),
    path("semana/", appointment_calendar, name="appointment_calendar"),
    path(
        "consultas/<uuid:appointment_id>/confirmar/",
        appointment_confirm,
        name="appointment_confirm",
    ),
    path(
        "consultas/<uuid:appointment_id>/remarcar/",
        appointment_reschedule,
        name="appointment_reschedule",
    ),
    path(
        "consultas/<uuid:appointment_id>/cancelar/",
        appointment_cancel,
        name="appointment_cancel",
    ),
    path(
        "consultas/<uuid:appointment_id>/concluir/",
        appointment_complete,
        name="appointment_complete",
    ),
    path(
        "consultas/<uuid:appointment_id>/falta/",
        appointment_no_show,
        name="appointment_no_show",
    ),
    # Waitlist (8.10.4.2)
    path("espera/", waitlist_list, name="waitlist_list"),
    path("espera/nova/", waitlist_add, name="waitlist_add"),
    path(
        "espera/<uuid:entry_id>/cancelar/",
        waitlist_cancel,
        name="waitlist_cancel",
    ),
    path(
        "espera/<uuid:entry_id>/encaixar/",
        waitlist_fill,
        name="waitlist_fill",
    ),
    # Units and rooms (8.10.1)
    path("unidades/", unit_list, name="unit_list"),
    path("unidades/nova/", unit_create, name="unit_create"),
    path("unidades/<uuid:unit_id>/editar/", unit_update, name="unit_update"),
    path(
        "unidades/<uuid:unit_id>/inativar/",
        unit_deactivate,
        name="unit_deactivate",
    ),
    path("salas/nova/", room_create, name="room_create"),
    path("salas/<uuid:room_id>/inativar/", room_deactivate, name="room_deactivate"),
    # Serviços e horários de atendimento que o app do paciente consome
    # (nomes com o namespace `scheduling:`; ver scheduling/setup_urls.py).
    path("", include("scheduling.setup_urls")),
]
