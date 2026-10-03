"""Configuração da clínica que o app consome: serviços, horários e recursos de crise.

Cobre as telas de equipe (acesso por papel, isolamento por clínica, fluxos completos),
os serviços de domínio que as sustentam (validação, auditoria) e os idiomas en/es.
"""

from __future__ import annotations

import gettext as gettext_module
import re
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import AuditEvent
from clinics.models import Clinic, ClinicConfiguration, ClinicMembership
from people.models import ProfessionalProfile
from scheduling import availability_services, catalog_services
from scheduling.models import (
    AvailabilityPattern,
    Room,
    ScheduleBlock,
    Service,
    Unit,
)
from scheduling.services import free_slots
from tests.aftercare_support import Stage, build_stage, make_patient_login
from tests.factories import ClinicMembershipFactory, UserFactory
from wellness import crisis_services
from wellness.models import MANDATORY_CRISIS_DISCLAIMER, CrisisResourceConfig
from wellness.selectors import crisis_resources_and_grounding

pytestmark = pytest.mark.django_db

SP = ZoneInfo("America/Sao_Paulo")

READ_ROUTES = [
    "scheduling:service_list",
    "scheduling:availability_list",
    "scheduling:availability_preview",
    "wellness:crisis_resources",
]
WRITE_ROUTES = ["scheduling:service_create", "scheduling:availability_create"]


# ── Montagem ────────────────────────────────────────────────────────────────


def _client(clinic: Clinic, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


def _service(clinic: Clinic, **overrides: Any) -> Service:
    values: dict[str, Any] = {
        "name": "Sessão individual",
        "duration_minutes": 50,
        "buffer_minutes": 10,
    }
    values.update(overrides)
    return Service.infrastructure_objects.create(clinic_id=clinic.pk, **values)


def _unit(clinic: Clinic, **overrides: Any) -> Unit:
    values: dict[str, Any] = {
        "name": "Unidade Centro",
        "timezone_name": "America/Sao_Paulo",
    }
    values.update(overrides)
    return Unit.infrastructure_objects.create(clinic_id=clinic.pk, **values)


def _professional(clinic: Clinic, name: str = "Helena Prado") -> User:
    user = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=user, role=ClinicMembership.Role.THERAPIST
    )
    ProfessionalProfile.infrastructure_objects.create(
        clinic_id=clinic.pk,
        user_id=user.pk,
        full_name=name,
        professional_email=f"{user.pk}@example.test",
        category="psychologist",
    )
    return user


def _configure_hours(
    clinic: Clinic,
    weekly_hours: dict[str, list[dict[str, str]]],
    timezone_name: str = "America/Sao_Paulo",
) -> None:
    ClinicConfiguration.infrastructure_objects.create(
        clinic_id=clinic.pk,
        legal_name="Clínica Exemplo Ltda.",
        display_name="Clínica Exemplo",
        administrative_email="contato@example.test",
        address_line_1="Rua Exemplo, 100",
        city="Recife",
        region="PE",
        postal_code="50000-000",
        country_code="BR",
        timezone_name=timezone_name,
        weekly_hours=weekly_hours,
    )


MONDAY_ONLY = {
    "monday": [
        {"start": "08:00", "end": "12:00"},
        {"start": "14:00", "end": "18:00"},
    ],
    "tuesday": [],
    "wednesday": [],
    "thursday": [],
    "friday": [],
    "saturday": [],
    "sunday": [],
}


def _pattern(
    clinic: Clinic,
    professional: User,
    unit: Unit,
    *,
    weekday: int = 0,
    start: time = time(9, 0),
    end: time = time(12, 0),
    valid_from: date | None = None,
    valid_until: date | None = None,
) -> AvailabilityPattern:
    return AvailabilityPattern.infrastructure_objects.create(
        clinic_id=clinic.pk,
        professional_id=professional.pk,
        unit_id=unit.pk,
        weekday=weekday,
        start_time=start,
        end_time=end,
        valid_from=valid_from or timezone.localdate() - timedelta(days=30),
        valid_until=valid_until,
    )


def _create_payload(professional: User, unit: Unit, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "professional": str(professional.pk),
        "unit": str(unit.pk),
        "room": "",
        "weekdays": ["0"],
        "start_time": "09:00",
        "end_time": "12:00",
        "valid_from": timezone.localdate().isoformat(),
        "valid_until": "",
    }
    data.update(overrides)
    return data


def _audit(clinic: Clinic, resource_type: str, action: str) -> int:
    return (
        AuditEvent.objects.for_clinic(clinic.pk)
        .filter(resource_type=resource_type, action=action)
        .count()
    )


def _request_id() -> UUID:
    return uuid4()


# ── Acesso ──────────────────────────────────────────────────────────────────


def test_anonymous_users_are_sent_to_login() -> None:
    client = Client()
    for name in [*READ_ROUTES, *WRITE_ROUTES]:
        response = client.get(reverse(name))
        assert (
            response.status_code == 302 and "/accounts/login/" in response["Location"]
        ), name


@pytest.mark.parametrize("route", READ_ROUTES)
def test_clinic_team_can_read_every_setup_screen(route: str) -> None:
    stage = build_stage()
    for user in (stage.admin, stage.therapist, stage.staff):
        response = _client(stage.clinic, user).get(reverse(route))
        assert response.status_code == 200, (route, user.pk)
        assert 'class="ae-navbar"' in response.content.decode()
        assert response["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("route", WRITE_ROUTES)
def test_only_the_clinic_admin_opens_the_write_screens(route: str) -> None:
    stage = build_stage()
    assert _client(stage.clinic, stage.admin).get(reverse(route)).status_code == 200
    for user in (stage.therapist, stage.staff):
        assert _client(stage.clinic, user).get(reverse(route)).status_code == 403


def test_patients_never_open_the_setup_screens() -> None:
    stage = build_stage()
    patient = make_patient_login(stage.clinic, stage.admin)
    client = _client(stage.clinic, patient.user)
    for name in [*READ_ROUTES, *WRITE_ROUTES]:
        assert client.get(reverse(name)).status_code == 403, name
    assert client.post(reverse("scheduling:service_create"), {}).status_code == 403


def test_non_admins_do_not_see_write_actions() -> None:
    stage = build_stage()
    _service(stage.clinic)
    pro = _professional(stage.clinic)
    _pattern(stage.clinic, pro, _unit(stage.clinic))
    for user in (stage.therapist, stage.staff):
        client = _client(stage.clinic, user)
        services = client.get(reverse("scheduling:service_list")).content.decode()
        assert reverse("scheduling:service_create") not in services
        assert "Inativar" not in services
        hours = client.get(reverse("scheduling:availability_list")).content.decode()
        assert reverse("scheduling:availability_create") not in hours
        assert "Remover" not in hours
        crisis = client.get(reverse("wellness:crisis_resources")).content.decode()
        assert "<textarea" not in crisis
        assert "Somente o administrador da clínica pode alterar" in crisis
    admin = _client(stage.clinic, stage.admin)
    assert (
        reverse("scheduling:service_create")
        in admin.get(reverse("scheduling:service_list")).content.decode()
    )


def test_writes_by_non_admins_are_refused_and_change_nothing() -> None:
    stage = build_stage()
    service = _service(stage.clinic)
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    for user in (stage.therapist, stage.staff):
        client = _client(stage.clinic, user)
        created = client.post(
            reverse("scheduling:service_create"),
            {"name": "Novo", "duration_minutes": 30, "buffer_minutes": 0},
        )
        assert created.status_code == 403
        assert (
            client.post(
                reverse("scheduling:service_deactivate", args=[service.pk])
            ).status_code
            == 403
        )
        assert (
            client.post(
                reverse("scheduling:availability_create"), _create_payload(pro, unit)
            ).status_code
            == 403
        )
        assert (
            client.post(
                reverse("wellness:crisis_resources"),
                {"emergency_medical_number": "190"},
            ).status_code
            == 403
        )
    assert Service.objects.for_clinic(stage.clinic.pk).count() == 1
    service.refresh_from_db()
    assert service.is_active
    assert not AvailabilityPattern.objects.for_clinic(stage.clinic.pk).exists()
    assert not CrisisResourceConfig.objects.for_clinic(stage.clinic.pk).exists()


def test_dangerous_actions_do_not_run_on_get() -> None:
    stage = build_stage()
    service = _service(stage.clinic)
    pro = _professional(stage.clinic)
    pattern = _pattern(stage.clinic, pro, _unit(stage.clinic))
    client = _client(stage.clinic, stage.admin)
    for name in ("scheduling:service_deactivate", "scheduling:service_activate"):
        assert client.get(reverse(name, args=[service.pk])).status_code == 405
    # GET na remoção só mostra a confirmação
    page = client.get(reverse("scheduling:availability_remove", args=[pattern.pk]))
    assert page.status_code == 200
    pattern.refresh_from_db()
    assert pattern.is_active


def test_pages_are_csp_safe_and_load_only_local_assets() -> None:
    stage = build_stage()
    _service(stage.clinic)
    pro = _professional(stage.clinic)
    _pattern(stage.clinic, pro, _unit(stage.clinic))
    client = _client(stage.clinic, stage.admin)
    for route in [*READ_ROUTES, *WRITE_ROUTES]:
        html = client.get(reverse(route)).content.decode()
        assert re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) == [], route
        assert not re.search(r"(?:src|href)=[\"']https?://", html), route


# ── Isolamento: IDs de outra clínica nunca abrem ────────────────────────────


def test_foreign_ids_in_urls_are_denied_and_unchanged() -> None:
    stage = build_stage()
    service = _service(stage.clinic)
    pro = _professional(stage.clinic)
    pattern = _pattern(stage.clinic, pro, _unit(stage.clinic))
    outsider = _client(stage.other_clinic, stage.other_admin)
    for url in (
        reverse("scheduling:service_update", args=[service.pk]),
        reverse("scheduling:availability_update", args=[pattern.pk]),
        reverse("scheduling:availability_remove", args=[pattern.pk]),
    ):
        assert outsider.get(url).status_code == 403, url
    for url in (
        reverse("scheduling:service_update", args=[service.pk]),
        reverse("scheduling:service_deactivate", args=[service.pk]),
        reverse("scheduling:service_activate", args=[service.pk]),
        reverse("scheduling:availability_update", args=[pattern.pk]),
        reverse("scheduling:availability_remove", args=[pattern.pk]),
    ):
        assert outsider.post(url, {}).status_code == 403, url
    service.refresh_from_db()
    pattern.refresh_from_db()
    assert service.is_active and pattern.is_active


def test_lists_show_only_the_active_clinic_data() -> None:
    stage = build_stage()
    _service(stage.clinic, name="Terapia de casal")
    _service(stage.other_clinic, name="Serviço da outra clínica")
    other_pro = _professional(stage.other_clinic, name="Outro Profissional")
    _pattern(stage.other_clinic, other_pro, _unit(stage.other_clinic))
    client = _client(stage.clinic, stage.admin)
    services = client.get(reverse("scheduling:service_list")).content.decode()
    assert "Terapia de casal" in services
    assert "Serviço da outra clínica" not in services
    hours = client.get(reverse("scheduling:availability_list")).content.decode()
    assert "Outro Profissional" not in hours
    preview = client.get(reverse("scheduling:availability_preview")).content.decode()
    assert "Outro Profissional" not in preview


def test_each_clinic_has_its_own_crisis_resources() -> None:
    stage = build_stage()
    admin = _client(stage.clinic, stage.admin)
    response = admin.post(
        reverse("wellness:crisis_resources"), _crisis_payload(emergency_fire="1930")
    )
    assert response.status_code == 302
    other = crisis_resources_and_grounding(clinic_id=stage.other_clinic.pk)
    assert other["emergency_fire"] == "193"
    outsider = _client(stage.other_clinic, stage.other_admin)
    page = outsider.get(reverse("wellness:crisis_resources")).content.decode()
    assert "1930" not in page


# ── Serviços ────────────────────────────────────────────────────────────────


def test_admin_creates_edits_and_toggles_a_service() -> None:
    stage = build_stage()
    client = _client(stage.clinic, stage.admin)
    form = client.get(reverse("scheduling:service_create")).content.decode()
    assert "Duração da consulta (minutos)" in form
    response = client.post(
        reverse("scheduling:service_create"),
        {
            "name": "  Terapia   individual ",
            "duration_minutes": 45,
            "buffer_minutes": 15,
        },
    )
    assert response.status_code == 302
    service = Service.objects.for_clinic(stage.clinic.pk).get()
    assert (service.name, service.duration_minutes, service.buffer_minutes) == (
        "Terapia individual",
        45,
        15,
    )
    assert service.is_active
    assert _audit(stage.clinic, "service", "create") == 1
    listing = client.get(response["Location"]).content.decode()
    assert "Terapia individual" in listing and "45 min" in listing

    response = client.post(
        reverse("scheduling:service_update", args=[service.pk]),
        {"name": "Terapia de casal", "duration_minutes": 60, "buffer_minutes": 10},
    )
    assert response.status_code == 302
    service.refresh_from_db()
    assert (service.name, service.duration_minutes) == ("Terapia de casal", 60)
    assert _audit(stage.clinic, "service", "update") == 1

    client.post(reverse("scheduling:service_deactivate", args=[service.pk]))
    service.refresh_from_db()
    assert not service.is_active
    inactive = client.get(reverse("scheduling:service_list")).content.decode()
    assert "Inativo" in inactive and "Nenhum serviço ativo" in inactive
    client.post(reverse("scheduling:service_activate", args=[service.pk]))
    service.refresh_from_db()
    assert service.is_active
    assert _audit(stage.clinic, "service", "update") == 3


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"name": "", "duration_minutes": 50, "buffer_minutes": 10}, "obrigatório"),
        ({"name": "X", "duration_minutes": 4, "buffer_minutes": 10}, "maior ou igual"),
        (
            {"name": "X", "duration_minutes": 481, "buffer_minutes": 10},
            "menor ou igual",
        ),
        (
            {"name": "X", "duration_minutes": 50, "buffer_minutes": 121},
            "menor ou igual",
        ),
        ({"name": "X", "duration_minutes": 50, "buffer_minutes": -1}, "maior ou igual"),
    ],
)
def test_invalid_service_data_shows_an_error_and_saves_nothing(
    data: dict[str, Any], message: str
) -> None:
    stage = build_stage()
    response = _client(stage.clinic, stage.admin).post(
        reverse("scheduling:service_create"), data
    )
    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Service.objects.for_clinic(stage.clinic.pk).exists()


def test_service_names_are_unique_per_clinic_ignoring_case() -> None:
    stage = build_stage()
    _service(stage.clinic, name="Sessão individual")
    _service(stage.other_clinic, name="Terapia de casal")
    client = _client(stage.clinic, stage.admin)
    response = client.post(
        reverse("scheduling:service_create"),
        {"name": "sessão INDIVIDUAL", "duration_minutes": 50, "buffer_minutes": 10},
    )
    assert response.status_code == 200
    assert "Já existe um serviço com este nome" in response.content.decode()
    # o mesmo nome em outra clínica não conflita
    ok = client.post(
        reverse("scheduling:service_create"),
        {"name": "Terapia de casal", "duration_minutes": 50, "buffer_minutes": 10},
    )
    assert ok.status_code == 302


def test_service_services_authorize_validate_and_audit() -> None:
    stage = build_stage()
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "name": "Avaliação",
        "duration_minutes": 60,
        "buffer_minutes": 0,
        "request_id": _request_id(),
    }
    for actor in (stage.therapist, stage.staff, stage.other_admin):
        with pytest.raises(PermissionDenied):
            catalog_services.create_service(actor=actor, **kwargs)
    service = catalog_services.create_service(actor=stage.admin, **kwargs)
    foreign = {**kwargs, "clinic_id": stage.other_clinic.pk}
    with pytest.raises(PermissionDenied):
        catalog_services.update_service(
            actor=stage.other_admin, service_id=service.pk, **foreign
        )
    with pytest.raises(PermissionDenied):
        catalog_services.set_service_active(
            clinic_id=stage.other_clinic.pk,
            actor=stage.other_admin,
            service_id=service.pk,
            is_active=False,
            request_id=_request_id(),
        )
    with pytest.raises(ValidationError):
        catalog_services.update_service(
            actor=stage.admin,
            service_id=service.pk,
            **{**kwargs, "duration_minutes": 0},
        )
    # ativar o que já está ativo não grava nem audita de novo
    before = _audit(stage.clinic, "service", "update")
    catalog_services.set_service_active(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        service_id=service.pk,
        is_active=True,
        request_id=_request_id(),
    )
    assert _audit(stage.clinic, "service", "update") == before


# ── Horários de atendimento ─────────────────────────────────────────────────


def test_admin_creates_the_same_window_on_several_weekdays() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic, name="Helena Prado")
    unit = _unit(stage.clinic)
    client = _client(stage.clinic, stage.admin)
    form = client.get(reverse("scheduling:availability_create")).content.decode()
    assert "Helena Prado" in form and "Unidade Centro" in form
    response = client.post(
        reverse("scheduling:availability_create"),
        _create_payload(pro, unit, weekdays=["0", "2", "4"]),
    )
    assert response.status_code == 302
    patterns = AvailabilityPattern.objects.for_clinic(stage.clinic.pk).order_by(
        "weekday"
    )
    assert [p.weekday for p in patterns] == [0, 2, 4]
    assert {(p.start_time, p.end_time) for p in patterns} == {(time(9), time(12))}
    assert _audit(stage.clinic, "availability_pattern", "create") == 3
    listing = client.get(response["Location"]).content.decode()
    for text in ("Helena Prado", "Segunda-feira", "Quarta-feira", "Sexta-feira"):
        assert text in listing
    assert "09:00–12:00" in listing and "Em vigor" in listing
    assert "Salvar horário" not in listing  # voltou para a lista


def test_availability_list_marks_future_and_ended_windows() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    today = timezone.localdate()
    _pattern(stage.clinic, pro, unit, weekday=0)
    _pattern(stage.clinic, pro, unit, weekday=1, valid_from=today + timedelta(days=10))
    _pattern(
        stage.clinic,
        pro,
        unit,
        weekday=2,
        valid_until=today - timedelta(days=1),
    )
    removed = _pattern(stage.clinic, pro, unit, weekday=3)
    removed.is_active = False
    removed.save()
    html = (
        _client(stage.clinic, stage.admin)
        .get(reverse("scheduling:availability_list"))
        .content.decode()
    )
    assert "Em vigor" in html and "Começa depois" in html and "Encerrado" in html
    assert "Quinta-feira" not in html  # removido não aparece


def test_overlapping_windows_of_the_same_professional_are_rejected() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    other_unit = _unit(stage.clinic, name="Unidade Norte")
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_create")
    assert client.post(url, _create_payload(pro, unit)).status_code == 302
    overlap = client.post(
        url, _create_payload(pro, unit, start_time="11:00", end_time="13:00")
    )
    assert overlap.status_code == 200
    assert "se sobrepõe" in overlap.content.decode()
    # a mesma pessoa não está em duas unidades ao mesmo tempo
    elsewhere = client.post(
        url, _create_payload(pro, other_unit, start_time="10:00", end_time="11:00")
    )
    assert elsewhere.status_code == 200 and "se sobrepõe" in elsewhere.content.decode()
    # janelas encostadas, outro dia e outro profissional são válidos
    assert (
        client.post(
            url, _create_payload(pro, unit, start_time="12:00", end_time="14:00")
        ).status_code
        == 302
    )
    assert (
        client.post(url, _create_payload(pro, unit, weekdays=["1"])).status_code == 302
    )
    other_pro = _professional(stage.clinic, name="Outro Nome")
    assert client.post(url, _create_payload(other_pro, unit)).status_code == 302
    assert AvailabilityPattern.objects.for_clinic(stage.clinic.pk).count() == 4


def test_overlap_considers_the_validity_period() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    today = timezone.localdate()
    availability_services.create_availability_pattern(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        professional_id=pro.pk,
        unit_id=unit.pk,
        room_id=None,
        weekday=0,
        start_time=time(9),
        end_time=time(12),
        valid_from=today,
        valid_until=today + timedelta(days=30),
        request_id=_request_id(),
    )
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.admin,
        "professional_id": pro.pk,
        "unit_id": unit.pk,
        "room_id": None,
        "weekday": 0,
        "start_time": time(9),
        "end_time": time(12),
        "request_id": _request_id(),
    }
    # começa depois do fim da primeira: não se sobrepõe
    availability_services.create_availability_pattern(
        valid_from=today + timedelta(days=31), valid_until=None, **kwargs
    )
    # a primeira ainda vale nestes dias
    with pytest.raises(ValidationError):
        availability_services.create_availability_pattern(
            valid_from=today + timedelta(days=10),
            valid_until=today + timedelta(days=12),
            **kwargs,
        )


def test_windows_must_fit_the_clinic_operating_hours() -> None:
    stage = build_stage()
    _configure_hours(stage.clinic, MONDAY_ONLY)
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_create")

    early = client.post(
        url, _create_payload(pro, unit, start_time="07:00", end_time="09:00")
    )
    assert early.status_code == 200
    assert "fora do funcionamento da clínica" in early.content.decode()
    across_lunch = client.post(
        url, _create_payload(pro, unit, start_time="11:00", end_time="15:00")
    )
    assert "fora do funcionamento da clínica" in across_lunch.content.decode()
    closed_day = client.post(url, _create_payload(pro, unit, weekdays=["6"]))
    assert "não funciona" in closed_day.content.decode()
    assert not AvailabilityPattern.objects.for_clinic(stage.clinic.pk).exists()

    inside = client.post(
        url, _create_payload(pro, unit, start_time="08:00", end_time="12:00")
    )
    assert inside.status_code == 302
    afternoon = client.post(
        url, _create_payload(pro, unit, start_time="14:00", end_time="18:00")
    )
    assert afternoon.status_code == 302


def test_operating_hours_are_not_enforced_when_not_configured() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_create")
    # clínica sem configuração de horários
    assert (
        client.post(
            url, _create_payload(pro, unit, start_time="05:00", end_time="06:00")
        ).status_code
        == 302
    )
    # configuração com todos os dias fechados = horários ainda não definidos
    _configure_hours(
        stage.other_clinic, {day: [] for day in ("monday", "tuesday", "sunday")}
    )
    other_pro = _professional(stage.other_clinic)
    other_unit = _unit(stage.other_clinic)
    availability_services.create_availability_pattern(
        clinic_id=stage.other_clinic.pk,
        actor=stage.other_admin,
        professional_id=other_pro.pk,
        unit_id=other_unit.pk,
        room_id=None,
        weekday=0,
        start_time=time(5),
        end_time=time(6),
        valid_from=timezone.localdate(),
        valid_until=None,
        request_id=_request_id(),
    )


def test_operating_hours_check_is_skipped_when_the_unit_uses_another_timezone() -> None:
    stage = build_stage()
    _configure_hours(stage.clinic, MONDAY_ONLY)
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic, name="Unidade Miami", timezone_name="America/New_York")
    created = availability_services.create_availability_pattern(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        professional_id=pro.pk,
        unit_id=unit.pk,
        room_id=None,
        weekday=6,
        start_time=time(5),
        end_time=time(6),
        valid_from=timezone.localdate(),
        valid_until=None,
        request_id=_request_id(),
    )
    assert created.pk


def test_form_rejects_inconsistent_times_dates_and_rooms() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    other_unit = _unit(stage.clinic, name="Unidade Norte")
    foreign_room = Room.infrastructure_objects.create(
        clinic_id=stage.clinic.pk, unit_id=other_unit.pk, name="Sala Norte"
    )
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_create")
    reversed_times = client.post(
        url, _create_payload(pro, unit, start_time="12:00", end_time="09:00")
    )
    assert "O fim deve ser depois do início" in reversed_times.content.decode()
    today = timezone.localdate()
    bad_dates = client.post(
        url,
        _create_payload(
            pro,
            unit,
            valid_from=today.isoformat(),
            valid_until=(today - timedelta(days=1)).isoformat(),
        ),
    )
    assert "A data final não pode ser anterior à inicial" in bad_dates.content.decode()
    wrong_room = client.post(url, _create_payload(pro, unit, room=str(foreign_room.pk)))
    assert "não pertence à unidade escolhida" in wrong_room.content.decode()
    no_weekday = client.post(url, _create_payload(pro, unit, weekdays=[]))
    assert no_weekday.status_code == 200
    assert not AvailabilityPattern.objects.for_clinic(stage.clinic.pk).exists()


def test_a_room_of_the_unit_is_accepted() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    room = Room.infrastructure_objects.create(
        clinic_id=stage.clinic.pk, unit_id=unit.pk, name="Sala 2"
    )
    client = _client(stage.clinic, stage.admin)
    page = client.get(reverse("scheduling:availability_create")).content.decode()
    assert "Unidade Centro — Sala 2" in page
    response = client.post(
        reverse("scheduling:availability_create"),
        _create_payload(pro, unit, room=str(room.pk)),
    )
    assert response.status_code == 302
    pattern = AvailabilityPattern.objects.for_clinic(stage.clinic.pk).get()
    assert pattern.room_id == room.pk
    assert "Sala 2" in client.get(response["Location"]).content.decode()


def test_only_active_therapists_and_units_of_the_clinic_are_offered() -> None:
    stage = build_stage()
    mine = _professional(stage.clinic, name="Helena Prado")
    _professional(stage.other_clinic, name="Profissional Alheio")
    _unit(stage.other_clinic, name="Unidade Alheia")
    inactive_unit = _unit(stage.clinic, name="Unidade Fechada", is_active=False)
    unit = _unit(stage.clinic)
    client = _client(stage.clinic, stage.admin)
    page = client.get(reverse("scheduling:availability_create")).content.decode()
    assert "Helena Prado" in page and "Unidade Centro" in page
    assert "Profissional Alheio" not in page and "Unidade Alheia" not in page
    assert "Unidade Fechada" not in page
    # tentar forçar valores de fora da lista é recusado
    outsider_user = UserFactory.create()
    for payload in (
        _create_payload(outsider_user, unit),
        _create_payload(mine, inactive_unit),
    ):
        response = client.post(reverse("scheduling:availability_create"), payload)
        assert response.status_code == 200
    assert not AvailabilityPattern.objects.for_clinic(stage.clinic.pk).exists()


def test_availability_services_validate_authorization_and_references() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    foreign_unit = _unit(stage.other_clinic)
    foreign_room = Room.infrastructure_objects.create(
        clinic_id=stage.other_clinic.pk, unit_id=foreign_unit.pk, name="Sala Alheia"
    )
    base: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "professional_id": pro.pk,
        "unit_id": unit.pk,
        "room_id": None,
        "weekday": 0,
        "start_time": time(9),
        "end_time": time(12),
        "valid_from": timezone.localdate(),
        "valid_until": None,
        "request_id": _request_id(),
    }
    for actor in (stage.therapist, stage.staff, stage.other_admin):
        with pytest.raises(PermissionDenied):
            availability_services.create_availability_pattern(actor=actor, **base)
    with pytest.raises(ValidationError):  # sala de outra clínica
        availability_services.create_availability_pattern(
            actor=stage.admin, **{**base, "room_id": foreign_room.pk}
        )
    with pytest.raises(ValidationError):  # unidade inativa
        inactive = _unit(stage.clinic, name="Fechada", is_active=False)
        availability_services.create_availability_pattern(
            actor=stage.admin, **{**base, "unit_id": inactive.pk}
        )
    with pytest.raises(ValidationError):  # nenhum dia
        availability_services.create_availability_patterns(
            actor=stage.admin,
            weekdays=[],
            **{k: v for k, v in base.items() if k != "weekday"},
        )
    assert not AvailabilityPattern.objects.for_clinic(stage.clinic.pk).exists()


def test_creating_several_weekdays_is_all_or_nothing() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    _pattern(stage.clinic, pro, unit, weekday=2)  # quarta já ocupada
    with pytest.raises(ValidationError):
        availability_services.create_availability_patterns(
            clinic_id=stage.clinic.pk,
            actor=stage.admin,
            professional_id=pro.pk,
            unit_id=unit.pk,
            room_id=None,
            weekdays=[0, 1, 2],
            start_time=time(9),
            end_time=time(12),
            valid_from=timezone.localdate(),
            valid_until=None,
            request_id=_request_id(),
        )
    assert AvailabilityPattern.objects.for_clinic(stage.clinic.pk).count() == 1


def test_admin_edits_a_window_and_it_is_audited() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    other_unit = _unit(stage.clinic, name="Unidade Norte")
    pattern = _pattern(stage.clinic, pro, unit, weekday=0)
    _pattern(stage.clinic, pro, unit, weekday=1, start=time(14), end=time(16))
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_update", args=[pattern.pk])
    page = client.get(url).content.decode()
    assert "Helena Prado" in page and 'value="09:00"' in page
    # ampliar a própria janela não conflita consigo mesma
    response = client.post(
        url,
        {
            "unit": str(other_unit.pk),
            "room": "",
            "weekday": "3",
            "start_time": "08:00",
            "end_time": "13:00",
            "valid_from": timezone.localdate().isoformat(),
            "valid_until": "",
        },
    )
    assert response.status_code == 302
    pattern.refresh_from_db()
    assert (pattern.weekday, pattern.unit_id) == (3, other_unit.pk)
    assert (pattern.start_time, pattern.end_time) == (time(8), time(13))
    assert _audit(stage.clinic, "availability_pattern", "update") == 1
    # mover para cima de outra janela do profissional é recusado
    clash = client.post(
        url,
        {
            "unit": str(unit.pk),
            "room": "",
            "weekday": "1",
            "start_time": "15:00",
            "end_time": "17:00",
            "valid_from": timezone.localdate().isoformat(),
            "valid_until": "",
        },
    )
    assert clash.status_code == 200 and "se sobrepõe" in clash.content.decode()
    pattern.refresh_from_db()
    assert pattern.weekday == 3


def test_removing_a_window_asks_for_confirmation_and_audits() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic, name="Helena Prado")
    pattern = _pattern(stage.clinic, pro, _unit(stage.clinic))
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_remove", args=[pattern.pk])
    confirm = client.get(url).content.decode()
    assert "Helena Prado" in confirm and "Consultas já marcadas" in confirm
    response = client.post(url)
    assert response.status_code == 302
    pattern.refresh_from_db()
    assert not pattern.is_active
    assert _audit(stage.clinic, "availability_pattern", "update") == 1
    # janela já removida não abre mais
    assert client.get(url).status_code == 403
    assert (
        client.get(
            reverse("scheduling:availability_update", args=[pattern.pk])
        ).status_code
        == 403
    )


# ── Prévia dos horários livres ──────────────────────────────────────────────


def _preview_total(html: str) -> int:
    return sum(int(n) for n in re.findall(r"Total: (\d+)", html))


def test_preview_matches_what_the_app_computes_for_patients() -> None:
    stage = build_stage()
    pro = _professional(stage.clinic, name="Helena Prado")
    unit = _unit(stage.clinic)
    service = _service(stage.clinic)  # 50 min + 10 de intervalo
    client = _client(stage.clinic, stage.admin)
    # a equipe cadastra os horários pela tela, todos os dias da semana
    client.post(
        reverse("scheduling:availability_create"),
        _create_payload(pro, unit, weekdays=[str(day) for day in range(7)]),
    )
    html = client.get(reverse("scheduling:availability_preview")).content.decode()
    assert "Helena Prado" in html and "Unidade Centro" in html
    assert 'ae-badge--info">10:00</span>' in html
    before = _preview_total(html)
    assert before >= 3 * 6  # 09:00, 10:00 e 11:00 nos dias futuros

    # o mesmo cálculo que alimenta /api/v1/mobile/booking/options/
    target = datetime.now(SP).date() + timedelta(days=3)
    slots = free_slots(
        clinic_id=stage.clinic.pk,
        professional_id=pro.pk,
        unit_id=unit.pk,
        service_id=service.pk,
        from_date=target,
        to_date=target,
    )
    assert [slot.strftime("%H:%M") for slot in slots] == ["09:00", "10:00", "11:00"]

    # um bloqueio de agenda reflete na prévia
    ScheduleBlock.infrastructure_objects.create(
        clinic_id=stage.clinic.pk,
        professional_id=pro.pk,
        unit_id=unit.pk,
        start_at=datetime.combine(target, time(9, 0), tzinfo=SP),
        end_at=datetime.combine(target, time(10, 0), tzinfo=SP),
    )
    after = _preview_total(
        client.get(reverse("scheduling:availability_preview")).content.decode()
    )
    assert after == before - 1


def test_preview_filters_by_service_and_professional() -> None:
    stage = build_stage()
    first = _professional(stage.clinic, name="Helena Prado")
    second = _professional(stage.clinic, name="Marcos Lima")
    unit = _unit(stage.clinic)
    short = _service(stage.clinic, name="Sessão curta", duration_minutes=30)
    _service(stage.clinic, name="Sessão longa", duration_minutes=60)
    inactive = _service(stage.clinic, name="Serviço antigo", is_active=False)
    for pro in (first, second):
        for day in range(7):
            _pattern(stage.clinic, pro, unit, weekday=day)
    client = _client(stage.clinic, stage.therapist)
    url = reverse("scheduling:availability_preview")
    both = client.get(url).content.decode()
    assert "Helena Prado" in both and "Marcos Lima" in both
    assert "Serviço antigo" not in both  # só serviços ativos
    only_second = client.get(
        url, {"service": str(short.pk), "professional": str(second.pk)}
    ).content.decode()
    assert "Marcos Lima" in only_second
    assert (
        "Helena Prado</h2>" not in only_second and "Helena Prado ·" not in only_second
    )
    assert "30 min de duração" in only_second
    # serviço inativo ou de outra clínica volta ao padrão com aviso
    foreign = _service(stage.other_clinic, name="Serviço alheio")
    for service_id in (inactive.pk, foreign.pk, "lixo"):
        response = client.get(url, {"service": str(service_id)})
        assert response.status_code == 200
        html = response.content.decode()
        assert "Escolha um serviço e um profissional da lista" in html
        assert "Serviço alheio" not in html


def test_preview_limits_the_combinations_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = build_stage()
    unit = _unit(stage.clinic)
    _service(stage.clinic)
    first = _professional(stage.clinic, name="Ana Souza")
    second = _professional(stage.clinic, name="Beto Lima")
    for pro in (first, second):
        _pattern(stage.clinic, pro, unit)
    monkeypatch.setattr("scheduling.availability_views.MAX_PREVIEW_PAIRS", 1)
    client = _client(stage.clinic, stage.admin)
    html = client.get(reverse("scheduling:availability_preview")).content.decode()
    assert "Ana Souza ·" in html and "Beto Lima ·" not in html
    assert "Há muitas combinações" in html
    # filtrar por profissional mostra quem ficou de fora
    only = client.get(
        reverse("scheduling:availability_preview"),
        {
            "service": str(Service.objects.for_clinic(stage.clinic.pk).get().pk),
            "professional": str(second.pk),
        },
    ).content.decode()
    assert "Beto Lima ·" in only and "Ana Souza ·" not in only
    assert "Há muitas combinações" not in only


def test_preview_explains_what_is_missing() -> None:
    stage = build_stage()
    client = _client(stage.clinic, stage.admin)
    url = reverse("scheduling:availability_preview")
    assert "Nenhum serviço ativo" in client.get(url).content.decode()
    _service(stage.clinic)
    assert (
        "Nenhum horário de atendimento cadastrado" in client.get(url).content.decode()
    )
    listing = client.get(reverse("scheduling:availability_list")).content.decode()
    assert "Sem horários, o paciente não consegue pedir consulta" in listing


# ── Recursos de crise ───────────────────────────────────────────────────────


def _crisis_payload(**overrides: str) -> dict[str, str]:
    data = {
        "emergency_medical_number": "192",
        "emergency_fire_number": "193",
        "emotional_support_number": "188",
        "custom_helpline_name": "",
        "custom_helpline_number": "",
        "mandatory_disclaimer_text": MANDATORY_CRISIS_DISCLAIMER,
    }
    mapping = {
        "emergency_fire": "emergency_fire_number",
        "emergency_medical": "emergency_medical_number",
        "support": "emotional_support_number",
        "helpline_name": "custom_helpline_name",
        "helpline_number": "custom_helpline_number",
        "disclaimer": "mandatory_disclaimer_text",
    }
    for key, value in overrides.items():
        data[mapping.get(key, key)] = value
    return data


def test_crisis_screen_shows_defaults_and_the_emergency_warning() -> None:
    stage = build_stage()
    html = (
        _client(stage.clinic, stage.admin)
        .get(reverse("wellness:crisis_resources"))
        .content.decode()
    )
    assert "O aplicativo não é um serviço de emergência" in html
    for number in ("192", "193", "188"):
        assert f">{number}<" in html
    assert "ainda não personalizou" in html
    assert 'name="mandatory_disclaimer_text"' in html


def test_admin_saves_the_crisis_resources_and_the_app_reads_them() -> None:
    stage = build_stage()
    client = _client(stage.clinic, stage.admin)
    extra = "Em horário comercial, ligue também para a recepção."
    response = client.post(
        reverse("wellness:crisis_resources"),
        _crisis_payload(
            emergency_medical="190",
            emergency_fire="193",
            support="188",
            helpline_name="Plantão da clínica",
            helpline_number="+55  81  3000 0000",
            disclaimer=f"{MANDATORY_CRISIS_DISCLAIMER}\n\n{extra}",
        ),
    )
    assert response.status_code == 302
    config = CrisisResourceConfig.objects.for_clinic(stage.clinic.pk).get()
    assert config.emergency_medical_number == "190"
    assert config.custom_helpline_name == "Plantão da clínica"
    assert config.custom_helpline_number == "+55 81 3000 0000"
    assert _audit(stage.clinic, "crisis_resource_config", "create") == 1
    # é o que /api/v1/mobile/help/ entrega ao paciente
    app = crisis_resources_and_grounding(clinic_id=stage.clinic.pk)
    assert app["emergency_medical"] == "190"
    assert app["custom_helpline"] == {
        "name": "Plantão da clínica",
        "number": "+55 81 3000 0000",
    }
    assert extra in app["mandatory_disclaimer"]
    assert MANDATORY_CRISIS_DISCLAIMER in app["mandatory_disclaimer"]
    page = client.get(response["Location"]).content.decode()
    assert (
        ">190<" in page and "Plantão da clínica" in page and "Última alteração" in page
    )

    again = client.post(
        reverse("wellness:crisis_resources"),
        _crisis_payload(
            emergency_medical="190",
            helpline_name="",
            helpline_number="",
            disclaimer=MANDATORY_CRISIS_DISCLAIMER,
        ),
    )
    assert again.status_code == 302
    assert _audit(stage.clinic, "crisis_resource_config", "update") == 1
    assert (
        crisis_resources_and_grounding(clinic_id=stage.clinic.pk)["custom_helpline"]
        is None
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"emergency_medical": "19a"},
        {"emergency_medical": "tel:192"},
        {"emergency_fire": "+"},
        {"emergency_fire": "1+93"},
        {"support": "18"},
        {"support": ""},
        {"emergency_medical": "1" * 17},
        {"helpline_name": "Plantão"},
        {"helpline_number": "3000 0000"},
        {"helpline_name": "Plantão", "helpline_number": "(81) 3000-0000"},
        {"helpline_name": "Plantão", "helpline_number": "+" + "9" * 16},
    ],
)
def test_invalid_numbers_are_rejected_with_a_visible_error(
    overrides: dict[str, str],
) -> None:
    stage = build_stage()
    response = _client(stage.clinic, stage.admin).post(
        reverse("wellness:crisis_resources"), _crisis_payload(**overrides)
    )
    assert response.status_code == 200
    assert 'class="ae-error"' in response.content.decode()
    assert not CrisisResourceConfig.objects.for_clinic(stage.clinic.pk).exists()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   \n  ",
        "Aviso próprio da clínica sem o texto padrão.",
        MANDATORY_CRISIS_DISCLAIMER[:-10],
        "x" * 1001,
    ],
)
def test_the_mandatory_notice_cannot_be_emptied_or_removed(text: str) -> None:
    stage = build_stage()
    response = _client(stage.clinic, stage.admin).post(
        reverse("wellness:crisis_resources"), _crisis_payload(disclaimer=text)
    )
    assert response.status_code == 200
    assert 'class="ae-error"' in response.content.decode()
    assert not CrisisResourceConfig.objects.for_clinic(stage.clinic.pk).exists()
    assert (
        crisis_resources_and_grounding(clinic_id=stage.clinic.pk)[
            "mandatory_disclaimer"
        ]
        == MANDATORY_CRISIS_DISCLAIMER
    )


def test_the_mandatory_notice_is_kept_even_when_the_form_is_bypassed() -> None:
    stage = build_stage()
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "emergency_medical_number": "192",
        "emergency_fire_number": "193",
        "emotional_support_number": "188",
        "custom_helpline_name": "",
        "custom_helpline_number": "",
        "request_id": _request_id(),
    }
    with pytest.raises(ValidationError):
        crisis_services.update_crisis_resources(
            actor=stage.admin, mandatory_disclaimer_text="  ", **kwargs
        )
    with pytest.raises(ValidationError):
        crisis_services.update_crisis_resources(
            actor=stage.admin, mandatory_disclaimer_text="Outro texto", **kwargs
        )
    with pytest.raises(ValidationError):
        crisis_services.update_crisis_resources(
            actor=stage.admin,
            mandatory_disclaimer_text=MANDATORY_CRISIS_DISCLAIMER,
            **{**kwargs, "emergency_medical_number": "javascript:1"},
        )
    for actor in (stage.therapist, stage.staff, stage.other_admin):
        with pytest.raises(PermissionDenied):
            crisis_services.update_crisis_resources(
                actor=actor,
                mandatory_disclaimer_text=MANDATORY_CRISIS_DISCLAIMER,
                **kwargs,
            )
    assert not CrisisResourceConfig.objects.for_clinic(stage.clinic.pk).exists()


def test_unchanged_crisis_settings_are_not_audited_again() -> None:
    stage = build_stage()
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.admin,
        "emergency_medical_number": "192",
        "emergency_fire_number": "193",
        "emotional_support_number": "188",
        "custom_helpline_name": "",
        "custom_helpline_number": "",
        "mandatory_disclaimer_text": MANDATORY_CRISIS_DISCLAIMER,
    }
    crisis_services.update_crisis_resources(request_id=_request_id(), **kwargs)
    crisis_services.update_crisis_resources(request_id=_request_id(), **kwargs)
    assert _audit(stage.clinic, "crisis_resource_config", "create") == 1
    assert _audit(stage.clinic, "crisis_resource_config", "update") == 0


# ── Idiomas (en/es) ─────────────────────────────────────────────────────────


class _TextNodes(HTMLParser):
    """Coleta os nós de texto visíveis (sem script/style), com espaços normalizados."""

    def __init__(self) -> None:
        super().__init__()
        self.nodes: set[str] = set()
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._skip:
            self.nodes.add(text)


def _text_nodes(html: str) -> set[str]:
    parser = _TextNodes()
    parser.feed(html)
    return parser.nodes


def _catalog(language: str) -> dict[str, str]:
    path = settings.BASE_DIR / "locale" / language / "LC_MESSAGES" / "django.mo"
    with path.open("rb") as source:
        catalog = vars(gettext_module.GNUTranslations(source))["_catalog"]
    return {k: v for k, v in catalog.items() if isinstance(k, str) and k}


def _seed_every_screen(stage: Stage) -> list[str]:
    service = _service(stage.clinic)
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    for day in range(7):
        _pattern(stage.clinic, pro, unit, weekday=day)
    pattern = AvailabilityPattern.objects.for_clinic(stage.clinic.pk).first()
    assert pattern is not None
    return [
        reverse("scheduling:service_list"),
        reverse("scheduling:service_create"),
        reverse("scheduling:service_update", args=[service.pk]),
        reverse("scheduling:availability_list"),
        reverse("scheduling:availability_create"),
        reverse("scheduling:availability_update", args=[pattern.pk]),
        reverse("scheduling:availability_remove", args=[pattern.pk]),
        reverse("scheduling:availability_preview"),
        reverse("wellness:crisis_resources"),
    ]


@pytest.mark.parametrize(
    ("language", "heading"),
    [
        ("en", "Crisis resources of the app"),
        ("es", "Recursos de crisis de la aplicación"),
    ],
)
def test_every_setup_screen_renders_in_english_and_spanish(
    language: str, heading: str
) -> None:
    stage = build_stage()
    urls = _seed_every_screen(stage)
    client = _client(stage.clinic, stage.admin)
    portuguese = _catalog("pt_BR")
    target = _catalog(language)
    # frases cujo texto muda de fato ao traduzir; não podem sobrar em português
    untranslated = {
        msgid for msgid in portuguese if target.get(msgid) not in {None, msgid}
    }
    # dados gravados pela equipe (e o aviso obrigatório, que é texto armazenado)
    user_data = {
        "Sessão individual",
        "Helena Prado",
        "Unidade Centro",
        " ".join(MANDATORY_CRISIS_DISCLAIMER.split()),
    }
    for url in urls:
        response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200, url
        html = response.content.decode()
        leaked = (_text_nodes(html) & untranslated) - user_data
        assert not leaked, f"{url}: sem tradução em {language}: {sorted(leaked)}"
    crisis = client.get(urls[-1], HTTP_ACCEPT_LANGUAGE=language).content.decode()
    assert heading in crisis


def test_weekday_and_validation_messages_follow_the_active_language() -> None:
    stage = build_stage()
    _configure_hours(stage.clinic, MONDAY_ONLY)
    pro = _professional(stage.clinic)
    unit = _unit(stage.clinic)
    _pattern(stage.clinic, pro, unit, weekday=0)
    client = _client(stage.clinic, stage.admin)
    english = client.get(
        reverse("scheduling:availability_list"), HTTP_ACCEPT_LANGUAGE="en"
    ).content.decode()
    assert "Monday" in english and "Segunda-feira" not in english
    overlap = client.post(
        reverse("scheduling:availability_create"),
        _create_payload(pro, unit, start_time="10:00", end_time="11:00"),
        HTTP_ACCEPT_LANGUAGE="en",
    ).content.decode()
    assert "overlaps another window" in overlap
    closed = client.post(
        reverse("scheduling:availability_create"),
        _create_payload(pro, unit, weekdays=["6"]),
        HTTP_ACCEPT_LANGUAGE="es",
    ).content.decode()
    assert "no funciona" in closed
    crisis = client.post(
        reverse("wellness:crisis_resources"),
        _crisis_payload(support="x"),
        HTTP_ACCEPT_LANGUAGE="en",
    ).content.decode()
    assert "Use only digits, spaces and a leading +" in crisis
