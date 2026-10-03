"""Telas de equipe de medicação, plano de cuidado e hábitos: acesso, tenant e fluxos."""

from __future__ import annotations

import gettext as gettext_module
import re
from datetime import timedelta
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditEvent
from people.models import CareRelationship, PatientProfile
from routines import care_plan_services, selectors
from routines import services as habit_services
from routines.medication_services import (
    grant_medication_share_consent,
    record_medication_dose,
    suspend_prescribed_medication,
)
from routines.models import (
    CarePlan,
    CarePlanStatus,
    Habit,
    HabitStatus,
    PatientResponseChoice,
    PrescribedMedication,
)
from tests.aftercare_support import make_patient, make_patient_login
from tests.routines_staff_support import (
    World,
    build_world,
    habit_form,
    hidden_fields,
    link,
    login,
    make_habit,
    make_medication,
    make_plan,
    medication_form,
    plan_form,
    today,
)

pytestmark = pytest.mark.django_db


def _audit(world: World, action: str) -> list[AuditEvent]:
    return list(
        AuditEvent.infrastructure_objects.filter(
            clinic_id=world.clinic.pk, action=action
        )
    )


def _url(name: str, world: World, *extra: Any) -> str:
    return reverse(f"routines:{name}", args=[world.patient.pk, *extra])


LIST_ROUTES = [
    "medication_list",
    "medication_create",
    "care_plan_list",
    "care_plan_create",
    "habit_list",
    "habit_create",
]


# ── Acesso ──────────────────────────────────────────────────────────────────


def test_anonymous_users_are_sent_to_login() -> None:
    world = build_world()
    client = Client()
    for name in LIST_ROUTES:
        response = client.get(_url(name, world))
        assert (
            response.status_code == 302 and "/accounts/login/" in response["Location"]
        )


@pytest.mark.parametrize("route", LIST_ROUTES)
def test_admin_and_linked_therapists_open_every_screen(route: str) -> None:
    world = build_world()
    for user in (world.admin, world.linked, world.second_linked):
        response = login(world.clinic, user).get(_url(route, world))
        assert response.status_code == 200, (route, user.pk)
        html = response.content.decode()
        assert 'class="ae-navbar"' in html  # layout do design system
        assert "Ana Souza" in html  # o paciente da URL, com breadcrumb próprio


@pytest.mark.parametrize("route", LIST_ROUTES)
def test_everyone_else_gets_the_same_403_without_leaking_the_patient(
    route: str,
) -> None:
    world = build_world()
    patient_login = make_patient_login(
        world.clinic, world.admin, name="Paciente do App"
    )
    own_url = reverse(f"routines:{route}", args=[patient_login.profile.pk])
    outsiders = [
        (login(world.clinic, world.unlinked), _url(route, world)),  # sem vínculo
        (login(world.clinic, world.stage.staff), _url(route, world)),  # administrativo
        (
            login(world.clinic, world.linked),
            reverse(f"routines:{route}", args=[world.other_patient.pk]),
        ),  # vínculo com outro paciente
        (login(world.clinic, patient_login.user), _url(route, world)),  # paciente
        (login(world.clinic, patient_login.user), own_url),  # o próprio cuidado
        (login(world.stage.other_clinic, world.stage.other_admin), _url(route, world)),
        (
            login(world.clinic, world.admin),
            reverse(f"routines:{route}", args=[uuid4()]),
        ),
    ]
    for client, url in outsiders:
        response = client.get(url)
        assert response.status_code == 403, url
        assert "Ana Souza" not in response.content.decode()


def test_therapist_link_must_be_current() -> None:
    world = build_world()
    ended = world.unlinked
    link(world.clinic, world.admin, ended, world.patient)
    assert login(world.clinic, ended).get(_url("habit_list", world)).status_code == 200
    CareRelationship.infrastructure_objects.filter(therapist=ended).update(
        valid_until=today() - timedelta(days=1)
    )
    assert login(world.clinic, ended).get(_url("habit_list", world)).status_code == 403


def test_pages_with_patient_data_are_never_cached() -> None:
    world = build_world()
    medication = make_medication(world)
    plan = make_plan(world)
    habit = make_habit(world)
    client = login(world.clinic, world.admin)
    for url in (
        _url("medication_list", world),
        _url("medication_create", world),
        _url("medication_edit", world, medication.pk),
        _url("care_plan_list", world),
        _url("care_plan_detail", world, plan.pk),
        _url("habit_list", world),
        _url("habit_edit", world, habit.pk),
    ):
        response = client.get(url)
        assert response.status_code == 200, url
        cache_control = response["Cache-Control"]
        assert "private" in cache_control and "no-store" in cache_control, url


def test_pages_are_csp_safe_and_load_only_local_assets() -> None:
    world = build_world()
    make_medication(world)
    make_plan(world)
    make_habit(world)
    client = login(world.clinic, world.admin)
    for route in LIST_ROUTES:
        html = client.get(_url(route, world)).content.decode()
        assert re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) == []
        assert not re.search(r"(?:src|href)=[\"']https?://", html)
        assert "fonts.googleapis.com" not in html


def test_each_screen_has_its_own_breadcrumb_and_care_navigation() -> None:
    world = build_world()
    html = (
        login(world.clinic, world.admin)
        .get(_url("care_plan_list", world))
        .content.decode()
    )
    assert reverse("patient_list") in html
    assert reverse("patient_detail", args=[world.patient.pk]) in html
    for name in ("medication_list", "care_plan_list", "habit_list"):
        assert _url(name, world) in html
    assert 'aria-current="page"' in html


# ── Isolamento: objeto de outro paciente ou de outra clínica ────────────────


def test_objects_of_another_patient_or_clinic_never_open_under_this_patient() -> None:
    world = build_world()
    # um objeto de cada tipo que NÃO pertence ao paciente da URL
    foreign_med = make_medication(world, world.other_patient)
    foreign_plan = make_plan(world, patient=world.other_patient)
    foreign_habit = make_habit(world, world.other_patient)
    outsider_patient = make_patient(world.stage.other_clinic, world.stage.other_admin)
    outside_med = make_medication(
        world, outsider_patient, clinic_id=world.stage.other_clinic.pk
    )
    admin = login(world.clinic, world.admin)
    gets = [
        ("medication_edit", foreign_med.pk),
        ("medication_stop", foreign_med.pk),
        ("medication_resume", foreign_med.pk),
        ("care_plan_detail", foreign_plan.pk),
        ("care_plan_edit", foreign_plan.pk),
        ("care_plan_submit", foreign_plan.pk),
        ("care_plan_reopen", foreign_plan.pk),
        ("care_plan_sign", foreign_plan.pk),
        ("care_plan_pause", foreign_plan.pk),
        ("care_plan_resume", foreign_plan.pk),
        ("care_plan_close", foreign_plan.pk),
        ("habit_edit", foreign_habit.pk),
        ("habit_pause", foreign_habit.pk),
        ("habit_archive", foreign_habit.pk),
        ("medication_edit", outside_med.pk),
    ]
    for name, object_id in gets:
        assert admin.get(_url(name, world, object_id)).status_code == 403, name
    for name in ("habit_resume",):
        assert admin.post(_url(name, world, foreign_habit.pk)).status_code == 403
    # uma tentativa de escrita também é negada e nada muda
    response = admin.post(
        _url("medication_stop", world, foreign_med.pk),
        {"kind": "suspend", "confirm": "on"},
    )
    assert response.status_code == 403
    foreign_med.refresh_from_db()
    assert foreign_med.is_active
    # e o administrador de outra clínica não alcança nada daqui
    outsider = login(world.stage.other_clinic, world.stage.other_admin)
    medication = make_medication(world)
    assert (
        outsider.get(_url("medication_edit", world, medication.pk)).status_code == 403
    )
    assert (
        outsider.post(
            _url("medication_stop", world, medication.pk),
            {"kind": "end", "confirm": "on"},
        ).status_code
        == 403
    )
    medication.refresh_from_db()
    assert medication.is_active


def test_dangerous_actions_do_not_run_on_get() -> None:
    world = build_world()
    habit = make_habit(world)
    habit_services.pause_habit(clinic_id=world.clinic.pk, habit_id=habit.pk)
    medication = make_medication(world)
    admin = login(world.clinic, world.admin)
    assert admin.get(_url("habit_resume", world, habit.pk)).status_code == 405
    habit.refresh_from_db()
    assert habit.status == HabitStatus.PAUSED
    # as telas de retirada só mostram a confirmação; nada muda no GET
    admin.get(_url("medication_stop", world, medication.pk))
    medication.refresh_from_db()
    assert medication.is_active


def test_write_screens_require_csrf_tokens_in_forms() -> None:
    world = build_world()
    medication = make_medication(world)
    admin = login(world.clinic, world.admin)
    for url in (
        _url("medication_create", world),
        _url("medication_stop", world, medication.pk),
        _url("care_plan_create", world),
        _url("habit_create", world),
    ):
        assert "csrfmiddlewaretoken" in admin.get(url).content.decode(), url


# ── Medicação ───────────────────────────────────────────────────────────────


def test_prescription_is_reviewed_and_only_published_after_explicit_confirmation() -> (
    None
):
    world = build_world()
    admin = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    page = admin.get(url).content.decode()
    assert "o paciente verá o nome, a dose" in page.lower()
    assert "Esta tela não sugere nem calcula doses" in page

    # 1) enviar o formulário só leva à revisão: nada é salvo
    review = admin.post(url, medication_form())
    assert review.status_code == 200
    html = review.content.decode()
    assert "Revisar antes de publicar" in html and "Nada foi salvo ainda" in html
    assert "08:00, 20:00" in html  # horários normalizados na conferência
    assert "Publicar no app do paciente" in html
    assert not PrescribedMedication.objects.for_clinic(world.clinic.pk).exists()
    assert (
        selectors.prescribed_medications_for_patient(
            clinic_id=world.clinic.pk, patient_profile_id=world.patient.pk
        )
        == []
    )

    # 2) publicar sem marcar a confirmação não salva
    data = hidden_fields(html) | {"action": "publish"}
    refused = admin.post(url, data)
    assert refused.status_code == 200
    assert "Marque a confirmação para continuar." in refused.content.decode()
    assert not PrescribedMedication.objects.for_clinic(world.clinic.pk).exists()

    # 3) com a confirmação, publica o que foi revisado (campos devolvidos pela página)
    response = admin.post(url, data | {"confirm": "on"})
    assert response.status_code == 302
    assert response["Location"] == _url("medication_list", world)
    medication = PrescribedMedication.objects.for_clinic(world.clinic.pk).get()
    assert medication.patient_profile_id == world.patient.pk
    assert medication.schedule_times == ["08:00", "20:00"]
    assert medication.is_continuous and medication.end_date is None
    assert medication.is_active
    # o app do paciente já enxerga
    assert (
        selectors.medication_for_patient(
            clinic_id=world.clinic.pk,
            patient_profile_id=world.patient.pk,
            medication_id=medication.pk,
        )
        is not None
    )
    events = _audit(world, "routines.medication_registered")
    assert len(events) == 1 and events[0].actor_id == world.admin.pk
    assert str(medication.pk) == events[0].resource_id
    listing = admin.get(response["Location"]).content.decode()
    assert "Sertralina" in listing and "Visível no app" in listing


def test_back_and_correct_returns_to_the_filled_form_without_saving() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    review = admin.post(url, medication_form()).content.decode()
    back = admin.post(url, hidden_fields(review) | {"action": "edit"})
    assert back.status_code == 200
    html = back.content.decode()
    assert 'value="Sertralina"' in html and "Revisar antes de publicar" in html
    assert "Nada foi salvo ainda" not in html
    assert not PrescribedMedication.objects.for_clinic(world.clinic.pk).exists()


def test_limited_course_roundtrips_through_the_review_step() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    end = (today() + timedelta(days=30)).isoformat()
    data = medication_form(end_date=end)
    data.pop("is_continuous")
    review = admin.post(url, data).content.decode()
    posted = hidden_fields(review) | {"action": "publish", "confirm": "on"}
    assert admin.post(url, posted).status_code == 302
    medication = PrescribedMedication.objects.for_clinic(world.clinic.pk).get()
    assert not medication.is_continuous
    assert medication.end_date == today() + timedelta(days=30)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"schedule_times": "25:00"}, "Horário inválido: 25:00"),
        ({"schedule_times": "oito da manhã"}, "Horário inválido: oito"),
        ({"schedule_times": " , "}, "Informe ao menos um horário."),
        (
            {"schedule_times": ", ".join(f"{h:02d}:00" for h in range(13))},
            "Informe no máximo 12 horários.",
        ),
        (
            {"instructions": "Se esquecer, tome o dobro na próxima."},
            "sugere mudar, compensar ou interromper a medicação",
        ),
        (
            {"instructions": "Aumente a dose se piorar."},
            "sugere mudar, compensar ou interromper a medicação",
        ),
        (
            {"is_continuous": "on", "end_date": "2030-01-01"},
            "Uso contínuo não tem data final",
        ),
        (
            {"prescription_date": (today() + timedelta(days=3)).isoformat()},
            "A data da receita não pode ser futura.",
        ),
        ({"prescriber_registration": ""}, "Registro do prescritor"),
        ({"prescriber_name": ""}, "Prescritor"),
        ({"medication_name": ""}, "Medicamento"),
        ({"route": "telepatia"}, "Via de administração"),
    ],
)
def test_prescription_validation_blocks_unsafe_or_incomplete_content(
    override: dict[str, str], message: str
) -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    response = admin.post(_url("medication_create", world), medication_form(**override))
    assert response.status_code == 200
    html = response.content.decode()
    assert message in html and "ae-field--error" in html
    assert "Nada foi salvo ainda" not in html  # nem chega à revisão
    assert not PrescribedMedication.objects.for_clinic(world.clinic.pk).exists()


def test_limited_course_needs_an_end_date_and_it_cannot_precede_the_start() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    data = medication_form()
    data.pop("is_continuous")
    missing = admin.post(url, data).content.decode()
    assert "Informe a data final ou marque o uso contínuo." in missing
    early = admin.post(
        url, data | {"end_date": (today() - timedelta(days=2)).isoformat()}
    ).content.decode()
    assert "A data final não pode ser anterior ao início." in early


def test_direct_publish_post_without_review_data_is_still_validated() -> None:
    """Um POST forjado com action=publish não pula a validação nem a confirmação."""
    world = build_world()
    admin = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    forged = medication_form(action="publish")
    response = admin.post(url, forged)
    assert response.status_code == 200
    assert "Marque a confirmação" in response.content.decode()
    assert not PrescribedMedication.objects.for_clinic(world.clinic.pk).exists()


def test_editing_a_prescription_goes_through_review_and_keeps_dose_history() -> None:
    world = build_world()
    medication = make_medication(world)
    record_medication_dose(
        clinic_id=world.clinic.pk,
        medication_id=medication.pk,
        scheduled_time=timezone.now() - timedelta(days=1),
        status="taken",
    )
    admin = login(world.clinic, world.admin)
    url = _url("medication_edit", world, medication.pk)
    page = admin.get(url).content.decode()
    assert 'value="Sertralina"' in page and "08:00, 20:00" in page
    data = medication_form(prescribed_dose="75 mg", schedule_times="09:00")
    review = admin.post(url, data)
    assert "Nada foi salvo ainda" in review.content.decode()
    medication.refresh_from_db()
    assert medication.prescribed_dose == "50 mg"  # ainda não mudou
    posted = hidden_fields(review.content.decode()) | {
        "action": "publish",
        "confirm": "on",
    }
    assert admin.post(url, posted).status_code == 302
    medication.refresh_from_db()
    assert medication.prescribed_dose == "75 mg"
    assert medication.schedule_times == ["09:00"]
    assert medication.logs.count() == 1  # registros de dose são mantidos
    assert len(_audit(world, "routines.medication_updated")) == 1


def test_suspend_resume_and_end_a_medication_with_confirmation() -> None:
    world = build_world()
    medication = make_medication(world)
    admin = login(world.clinic, world.admin)
    stop = _url("medication_stop", world, medication.pk)
    page = admin.get(stop).content.decode()
    assert "sai do app do paciente assim que você confirmar" in page

    unconfirmed = admin.post(stop, {"kind": "suspend"})
    assert unconfirmed.status_code == 200
    medication.refresh_from_db()
    assert medication.is_active

    assert admin.post(stop, {"kind": "suspend", "confirm": "on"}).status_code == 302
    medication.refresh_from_db()
    assert not medication.is_active
    assert (
        selectors.medication_for_patient(
            clinic_id=world.clinic.pk,
            patient_profile_id=world.patient.pk,
            medication_id=medication.pk,
        )
        is None
    )  # saiu do app
    listing = admin.get(_url("medication_list", world)).content.decode()
    assert (
        "Suspenso" in listing
        and _url("medication_resume", world, medication.pk) in listing
    )
    # suspenso só oferece encerrar, não suspender de novo
    again = admin.get(stop).content.decode()
    assert "Suspender: sai do app" not in again and "Encerrar o tratamento" in again

    resume = _url("medication_resume", world, medication.pk)
    assert admin.post(resume, {}).status_code == 200  # sem confirmação
    assert admin.post(resume, {"confirm": "on"}).status_code == 302
    medication.refresh_from_db()
    assert medication.is_active

    assert admin.post(stop, {"kind": "end", "confirm": "on"}).status_code == 302
    medication.refresh_from_db()
    assert not medication.is_active and not medication.is_continuous
    assert medication.end_date == today()
    listing = admin.get(_url("medication_list", world)).content.decode()
    assert "Encerrado" in listing
    # encerrado não volta e não se edita
    assert admin.get(resume).status_code == 302
    assert admin.get(_url("medication_edit", world, medication.pk)).status_code == 302
    assert admin.get(stop).status_code == 302
    medication.refresh_from_db()
    assert not medication.is_active
    for action in ("suspended", "resumed", "ended"):
        assert len(_audit(world, f"routines.medication_{action}")) >= 1


def test_course_that_already_ended_is_flagged_but_stays_editable() -> None:
    world = build_world()
    make_medication(
        world,
        is_continuous=False,
        start_date=today() - timedelta(days=20),
        end_date=today() - timedelta(days=2),
    )
    html = (
        login(world.clinic, world.admin)
        .get(_url("medication_list", world))
        .content.decode()
    )
    assert "Curso terminado" in html


def test_medication_list_orders_visible_first_and_empty_state_is_explicit() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    empty = admin.get(_url("medication_list", world)).content.decode()
    assert "Nenhuma medicação registrada" in empty
    suspended = make_medication(world, medication_name="Zolpidem")
    visible = make_medication(world, medication_name="Sertralina")
    suspend_prescribed_medication(
        clinic_id=world.clinic.pk,
        patient_profile_id=world.patient.pk,
        medication_id=suspended.pk,
        actor_id=world.admin.pk,
    )
    html = admin.get(_url("medication_list", world)).content.decode()
    assert html.index(visible.medication_name) < html.index("Zolpidem")


def test_adherence_is_read_only_and_reflects_the_patient_records() -> None:
    world = build_world()
    medication = make_medication(world)
    for offset, status in ((1, "taken"), (2, "late"), (3, "omitted")):
        record_medication_dose(
            clinic_id=world.clinic.pk,
            medication_id=medication.pk,
            scheduled_time=timezone.now() - timedelta(days=offset),
            status=status,
        )
    admin = login(world.clinic, world.admin)
    html = admin.get(_url("medication_list", world)).content.decode()
    assert "Registros de dose recentes" in html
    assert "Tomada com atraso" in html and "Não tomada" in html
    # só leitura: a página não tem controle algum para registrar dose
    assert "scheduled_time" not in html and "/doses/" not in html
    reads = [
        event
        for event in _audit(world, "view")
        if event.resource_type == "medication_adherence"
    ]
    assert reads and reads[0].resource_id == str(world.patient.pk)  # leitura auditada


def test_adherence_needs_consent_for_therapists_but_not_for_the_admin() -> None:
    world = build_world()
    patient_login = make_patient_login(world.clinic, world.admin, name="Com Login")
    medication = make_medication(world, patient_login.profile)
    record_medication_dose(
        clinic_id=world.clinic.pk,
        medication_id=medication.pk,
        scheduled_time=timezone.now() - timedelta(days=1),
        status="taken",
    )
    link(world.clinic, world.admin, world.linked, patient_login.profile)
    url = reverse("routines:medication_list", args=[patient_login.profile.pk])
    therapist = login(world.clinic, world.linked)
    html = therapist.get(url).content.decode()
    assert "só aparecem para quem recebeu o consentimento" in html
    assert "Registros de dose recentes" not in html
    grant_medication_share_consent(
        clinic_id=world.clinic.pk,
        patient_profile_id=patient_login.profile.pk,
        granted_to_user_id=world.linked.pk,
        actor_id=patient_login.user.pk,
    )
    assert "Registros de dose recentes" in therapist.get(url).content.decode()
    assert (
        "Registros de dose recentes"
        in login(world.clinic, world.admin).get(url).content.decode()
    )


def test_doses_of_other_patients_never_show_in_this_patients_adherence() -> None:
    world = build_world()
    foreign = make_medication(world, world.other_patient, medication_name="Lítio")
    record_medication_dose(
        clinic_id=world.clinic.pk,
        medication_id=foreign.pk,
        scheduled_time=timezone.now() - timedelta(days=1),
        status="taken",
    )
    html = (
        login(world.clinic, world.admin)
        .get(_url("medication_list", world))
        .content.decode()
    )
    assert "Lítio" not in html and "Registros de dose recentes" not in html


# ── Plano de cuidado ────────────────────────────────────────────────────────


def test_care_plan_flows_from_draft_to_active_with_explicit_signature() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    create = _url("care_plan_create", world)
    page = admin.get(create).content.decode()
    assert (
        "Isto é um rascunho" in page and "Justificativa clínica (uso interno)" in page
    )
    response = admin.post(create, plan_form())
    assert response.status_code == 302
    plan = CarePlan.objects.for_clinic(world.clinic.pk).get()
    assert response["Location"] == _url("care_plan_detail", world, plan.pk)
    assert plan.status == CarePlanStatus.DRAFT
    assert plan.prescribing_professional_id == world.admin.pk
    assert [a.action_description for a in plan.actions.all()] == [
        "Caminhada leve",
        "Anotar como foi o dia",
    ]
    assert plan.actions.first().is_mandatory  # type: ignore[union-attr]

    def visible_to_patient() -> CarePlan | None:
        return selectors.current_care_plan_for_patient(
            clinic_id=world.clinic.pk, patient_profile_id=world.patient.pk
        )

    assert visible_to_patient() is None  # rascunho nunca aparece no app
    detail = admin.get(response["Location"]).content.decode()
    assert "O paciente ainda não vê este plano" in detail
    assert (
        "Raciocínio clínico interno do caso." in detail
    )  # a equipe vê a justificativa
    assert _url("care_plan_sign", world, plan.pk) not in detail  # ainda não assina

    submit = _url("care_plan_submit", world, plan.pk)
    assert admin.post(submit, {}).status_code == 200  # sem confirmar
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.DRAFT
    assert admin.post(submit, {"confirm": "on"}).status_code == 302
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PENDING_SIGNATURE
    assert visible_to_patient() is None  # aguardando assinatura também não aparece
    detail = admin.get(_url("care_plan_detail", world, plan.pk)).content.decode()
    assert _url("care_plan_sign", world, plan.pk) in detail
    assert _url("care_plan_edit", world, plan.pk) not in detail

    sign = _url("care_plan_sign", world, plan.pk)
    preview = admin.get(sign).content.decode()
    assert "Como o paciente vai ver" in preview
    assert "Raciocínio clínico interno do caso." not in preview  # não vai ao paciente
    assert "Ao assinar, o plano aparece imediatamente no app do paciente" in preview
    assert admin.post(sign, {}).status_code == 200
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PENDING_SIGNATURE
    assert admin.post(sign, {"confirm": "on"}).status_code == 302
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.ACTIVE
    assert plan.signed_at is not None and len(plan.signature_digest) == 64
    assert visible_to_patient() is not None
    signed = _audit(world, "routines.care_plan_signed")
    assert len(signed) == 1 and signed[0].actor_id == world.admin.pk
    for action in ("proposed", "submitted"):
        assert len(_audit(world, f"routines.care_plan_{action}")) == 1
    listing = admin.get(_url("care_plan_list", world)).content.decode()
    assert "Plano de retorno gradual" in listing and "Ativo" in listing


def test_only_the_proposing_professional_edits_submits_or_signs() -> None:
    world = build_world()
    plan = make_plan(world, author=world.linked)
    other = login(world.clinic, world.second_linked)
    admin = login(world.clinic, world.admin)
    # outros profissionais com acesso ao paciente leem o plano, mas não o conduzem
    for client in (other, admin):
        assert client.get(_url("care_plan_detail", world, plan.pk)).status_code == 200
        for name in ("care_plan_edit", "care_plan_submit"):
            assert client.get(_url(name, world, plan.pk)).status_code == 403, name
        assert (
            client.post(
                _url("care_plan_submit", world, plan.pk), {"confirm": "on"}
            ).status_code
            == 403
        )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.DRAFT
    author = login(world.clinic, world.linked)
    assert (
        author.post(
            _url("care_plan_submit", world, plan.pk), {"confirm": "on"}
        ).status_code
        == 302
    )
    for client in (other, admin):
        assert client.get(_url("care_plan_sign", world, plan.pk)).status_code == 403
        assert (
            client.post(
                _url("care_plan_sign", world, plan.pk), {"confirm": "on"}
            ).status_code
            == 403
        )
        assert client.get(_url("care_plan_reopen", world, plan.pk)).status_code == 403
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PENDING_SIGNATURE
    detail = other.get(_url("care_plan_detail", world, plan.pk)).content.decode()
    assert _url("care_plan_sign", world, plan.pk) not in detail


def test_editing_a_draft_replaces_the_actions_and_pending_goes_back_to_draft() -> None:
    world = build_world()
    plan = make_plan(world)
    admin = login(world.clinic, world.admin)
    edit = _url("care_plan_edit", world, plan.pk)
    page = admin.get(edit).content.decode()
    assert 'value="Caminhada leve"' in page
    data = plan_form(
        title="Plano revisado",
        **{
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "1",
            "form-0-description": "Caminhada leve",
            "form-0-DELETE": "on",
            "form-1-description": "Alongar ao acordar",
            "form-1-target_frequency": "Diária",
            "form-2-description": "",
            "form-2-target_frequency": "",
        },
    )
    assert admin.post(edit, data).status_code == 302
    plan.refresh_from_db()
    assert plan.title == "Plano revisado"
    assert [a.action_description for a in plan.actions.all()] == ["Alongar ao acordar"]
    assert len(_audit(world, "routines.care_plan_updated")) == 1

    assert (
        admin.post(
            _url("care_plan_submit", world, plan.pk), {"confirm": "on"}
        ).status_code
        == 302
    )
    assert admin.get(edit).status_code == 302  # aguardando assinatura não se edita
    reopen = _url("care_plan_reopen", world, plan.pk)
    assert admin.post(reopen, {"confirm": "on"}).status_code == 302
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.DRAFT
    assert admin.get(edit).status_code == 200


def test_care_plan_form_validation() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    create = _url("care_plan_create", world)
    blank = {
        f"form-{i}-{field}": ""
        for i in range(2)
        for field in ("description", "target_frequency", "guidance", "is_mandatory")
    }
    no_actions = plan_form(**blank)
    response = admin.post(create, no_actions)
    assert response.status_code == 200
    assert "Inclua ao menos uma ação no plano." in response.content.decode()
    inverted = plan_form(valid_until=(today() - timedelta(days=3)).isoformat())
    response = admin.post(create, inverted)
    assert "A data final não pode ser anterior ao início." in response.content.decode()
    missing = plan_form(title="", clinical_rationale="")
    response = admin.post(create, missing)
    html = response.content.decode()
    assert html.count("Este campo é obrigatório.") >= 2
    half_filled = plan_form(**{"form-2-guidance": "Orientação sem ação"})
    half = admin.post(create, half_filled).content.decode()
    assert "Revise as ações do plano" in half
    assert not CarePlan.objects.for_clinic(world.clinic.pk).exists()


def test_patient_reply_is_shown_read_only_with_its_date() -> None:
    world = build_world()
    plan = make_plan(world, status="active")
    admin = login(world.clinic, world.admin)
    detail_url = _url("care_plan_detail", world, plan.pk)
    html = admin.get(detail_url).content.decode()
    assert "O paciente ainda não respondeu a esta versão do plano" in html
    assert "O paciente vê o título, o objetivo, as ações e os cuidados" in html

    care_plan_services.respond_to_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=plan.pk,
        decision=PatientResponseChoice.REVIEW_REQUESTED,
        patient_notes="Podemos reduzir a frequência?",
    )
    html = admin.get(detail_url).content.decode()
    assert "Pediu revisão do plano" in html
    assert "Podemos reduzir a frequência?" in html
    listing = admin.get(_url("care_plan_list", world)).content.decode()
    assert "Pediu revisão do plano" in listing


def test_patient_pause_then_team_resume_and_patient_refusal_closes_the_plan() -> None:
    world = build_world()
    plan = make_plan(world, status="active")
    admin = login(world.clinic, world.admin)
    care_plan_services.respond_to_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=plan.pk,
        decision=PatientResponseChoice.PAUSED,
    )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PAUSED
    resume = _url("care_plan_resume", world, plan.pk)
    page = admin.get(resume).content.decode()
    assert "O paciente pausou este plano" in page  # só retomar depois de combinar
    assert admin.post(resume, {}).status_code == 200
    assert admin.post(resume, {"confirm": "on"}).status_code == 302
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.ACTIVE

    care_plan_services.respond_to_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=plan.pk,
        decision=PatientResponseChoice.REFUSED,
    )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.REVOKED
    html = admin.get(_url("care_plan_detail", world, plan.pk)).content.decode()
    assert "Recusou o plano" in html
    assert "O plano foi encerrado pela recusa do paciente" in html
    # um plano recusado não volta a valer: nem assinando de novo, nem retomando
    for name in ("care_plan_sign", "care_plan_resume", "care_plan_pause"):
        assert admin.get(_url(name, world, plan.pk)).status_code == 302
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.REVOKED


def test_pause_and_close_an_active_plan() -> None:
    world = build_world()
    plan = make_plan(world, status="active")
    admin = login(world.clinic, world.admin)
    pause = _url("care_plan_pause", world, plan.pk)
    assert "marcado como pausado" in admin.get(pause).content.decode()
    assert admin.post(pause, {}).status_code == 200
    assert admin.post(pause, {"confirm": "on"}).status_code == 302
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PAUSED
    close = _url("care_plan_close", world, plan.pk)
    assert admin.post(close, {"outcome": "completed"}).status_code == 200
    assert admin.post(close, {"outcome": "draft", "confirm": "on"}).status_code == 200
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PAUSED
    assert (
        admin.post(close, {"outcome": "completed", "confirm": "on"}).status_code == 302
    )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.COMPLETED
    # encerrado é definitivo
    assert admin.get(close).status_code == 302
    html = admin.get(_url("care_plan_detail", world, plan.pk)).content.decode()
    assert "não aceita novas respostas" in html
    for action in ("paused", "closed"):
        assert len(_audit(world, f"routines.care_plan_{action}")) == 1


def test_revoking_through_the_team_screen_only_works_on_published_plans() -> None:
    world = build_world()
    draft = make_plan(world)
    admin = login(world.clinic, world.admin)
    assert admin.get(_url("care_plan_close", world, draft.pk)).status_code == 302
    response = admin.post(
        _url("care_plan_close", world, draft.pk),
        {"outcome": "revoked", "confirm": "on"},
    )
    assert response.status_code == 302
    draft.refresh_from_db()
    assert draft.status == CarePlanStatus.DRAFT  # revoked é visível ao paciente


def test_a_second_plan_cannot_be_signed_while_one_is_in_force() -> None:
    world = build_world()
    current = make_plan(world, status="active")
    pending = make_plan(world, status="pending_signature")
    admin = login(world.clinic, world.admin)
    sign = _url("care_plan_sign", world, pending.pk)
    response = admin.get(sign)
    assert response.status_code == 302
    followed = admin.get(response["Location"]).content.decode()
    assert "já tem um plano em vigor" in followed
    assert admin.post(sign, {"confirm": "on"}).status_code == 302
    pending.refresh_from_db()
    assert pending.status == CarePlanStatus.PENDING_SIGNATURE
    # encerrado o plano em vigor, assina
    assert (
        admin.post(
            _url("care_plan_close", world, current.pk),
            {"outcome": "completed", "confirm": "on"},
        ).status_code
        == 302
    )
    assert admin.post(sign, {"confirm": "on"}).status_code == 302
    pending.refresh_from_db()
    assert pending.status == CarePlanStatus.ACTIVE


def test_care_plan_screens_say_when_the_patient_will_see_each_state() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    expectations = {
        "draft": "O paciente ainda não vê este plano. Ele só aparece no app depois",
        "pending_signature": "Ele passa a aparecer no app",
        "active": "pode aceitar, pausar, recusar ou pedir revisão",
        "paused": "marcado como pausado",
    }
    for status, text in expectations.items():
        plan = make_plan(world, status=status)
        html = admin.get(_url("care_plan_detail", world, plan.pk)).content.decode()
        assert text in html, status
        if status in {"active", "paused"}:
            care_plan_services.close_care_plan(
                clinic_id=world.clinic.pk,
                patient_profile_id=world.patient.pk,
                care_plan_id=plan.pk,
                professional_user=world.admin,
            )


# ── Hábitos ─────────────────────────────────────────────────────────────────


def test_creating_and_editing_a_habit_publishes_to_the_app() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    create = _url("habit_create", world)
    page = admin.get(create).content.decode()
    assert "O paciente verá este hábito no app assim que você salvar" in page
    assert "America/Sao_Paulo" in page
    response = admin.post(
        create,
        habit_form(
            frequency="specific_days",
            active_days=["0", "2", "4"],
            time_window="exact_time",
            target_time="07:30",
            target_duration_minutes="15",
        ),
    )
    assert response.status_code == 302
    habit = Habit.objects.for_clinic(world.clinic.pk).get()
    assert habit.patient_profile_id == world.patient.pk
    assert habit.active_days == [0, 2, 4]
    assert habit.time_window == "exact_time"
    assert habit.target_time.strftime("%H:%M") == "07:30"  # type: ignore[union-attr]
    assert habit.target_duration_minutes == 15
    assert habit.timezone_name == world.patient.timezone_name
    assert (
        selectors.habit_for_patient(
            clinic_id=world.clinic.pk,
            patient_profile_id=world.patient.pk,
            habit_id=habit.pk,
        )
        is not None
    )
    events = _audit(world, "routines.habit_created")
    assert len(events) == 1 and events[0].actor_id == world.admin.pk
    listing = admin.get(response["Location"]).content.decode()
    assert "Beber água" in listing and "Seg, Qua, Sex" in listing and "07:30" in listing

    edit = _url("habit_edit", world, habit.pk)
    assert 'value="Beber água"' in admin.get(edit).content.decode()
    response = admin.post(
        edit,
        habit_form(
            title="Beber mais água",
            frequency="weekdays",
            time_window="afternoon",
            target_duration_minutes="",
        ),
    )
    assert response.status_code == 302
    habit.refresh_from_db()
    assert habit.title == "Beber mais água"
    assert habit.active_days == [0, 1, 2, 3, 4]
    assert habit.time_window == "afternoon"
    assert habit.target_time is None  # o horário fixo foi removido
    assert habit.target_duration_minutes == 0
    assert habit.version == 2
    assert len(_audit(world, "routines.habit_updated")) == 1


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"frequency": "specific_days"}, "Escolha ao menos um dia da semana."),
        ({"time_window": "exact_time"}, "Informe o horário do hábito."),
        ({"target_duration_minutes": "9999"}, "Duração em minutos"),
        ({"target_duration_minutes": "-3"}, "Duração em minutos"),
        ({"title": ""}, "Hábito"),
        ({"frequency": "sempre"}, "Frequência"),
    ],
)
def test_habit_form_validation(override: dict[str, str], message: str) -> None:
    world = build_world()
    response = login(world.clinic, world.admin).post(
        _url("habit_create", world), habit_form(**override)
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert message in html and "ae-field--error" in html
    assert not Habit.objects.for_clinic(world.clinic.pk).exists()


def test_pause_resume_and_archive_a_habit() -> None:
    world = build_world()
    habit = make_habit(world)
    admin = login(world.clinic, world.admin)
    pause = _url("habit_pause", world, habit.pk)
    assert "não consegue registrá-lo" in admin.get(pause).content.decode()
    past = (today() - timedelta(days=1)).isoformat()
    bad = admin.post(pause, {"paused_until": past})
    assert (
        bad.status_code == 200 and "não pode estar no passado" in bad.content.decode()
    )
    until = today() + timedelta(days=7)
    assert admin.post(pause, {"paused_until": until.isoformat()}).status_code == 302
    habit.refresh_from_db()
    assert habit.status == HabitStatus.PAUSED and habit.paused_until == until
    # pausado: o paciente não consegue registrar o dia
    assert (
        habit_services.ensure_habit_occurrence(
            clinic_id=world.clinic.pk, habit_id=habit.pk, scheduled_date=today()
        )
        is None
    )
    listing = admin.get(_url("habit_list", world)).content.decode()
    assert "Pausado" in listing and _url("habit_resume", world, habit.pk) in listing
    assert admin.get(pause).status_code == 302  # só ativo pausa

    resume = _url("habit_resume", world, habit.pk)
    assert admin.post(resume).status_code == 302
    habit.refresh_from_db()
    assert habit.status == HabitStatus.ACTIVE and habit.paused_until is None

    archive = _url("habit_archive", world, habit.pk)
    assert admin.post(archive, {}).status_code == 200
    assert admin.post(archive, {"confirm": "on"}).status_code == 302
    habit.refresh_from_db()
    assert habit.status == HabitStatus.ARCHIVED
    assert (
        selectors.habit_for_patient(
            clinic_id=world.clinic.pk,
            patient_profile_id=world.patient.pk,
            habit_id=habit.pk,
        )
        is None
    )  # saiu do app
    listing = admin.get(_url("habit_list", world)).content.decode()
    assert "Arquivados" in listing
    assert _url("habit_edit", world, habit.pk) not in listing
    # arquivado não se edita, pausa, retoma nem arquiva de novo
    assert admin.get(_url("habit_edit", world, habit.pk)).status_code == 302
    assert admin.get(pause).status_code == 302
    assert admin.post(resume).status_code == 302
    assert admin.get(archive).status_code == 302
    habit.refresh_from_db()
    assert habit.status == HabitStatus.ARCHIVED
    for action in ("paused", "resumed", "archived"):
        assert len(_audit(world, f"routines.habit_{action}")) == 1


def test_recent_checkins_made_by_the_patient_are_listed_read_only() -> None:
    world = build_world()
    habit = make_habit(world)
    for offset, status in ((0, "completed"), (1, "partial"), (2, "skipped")):
        occurrence = habit_services.ensure_habit_occurrence(
            clinic_id=world.clinic.pk,
            habit_id=habit.pk,
            scheduled_date=today() - timedelta(days=offset),
        )
        assert occurrence is not None
        habit_services.record_habit_checkin(
            clinic_id=world.clinic.pk, occurrence_id=occurrence.pk, status=status
        )
    foreign = make_habit(world, world.other_patient, title="Hábito de outra pessoa")
    foreign_occ = habit_services.ensure_habit_occurrence(
        clinic_id=world.clinic.pk, habit_id=foreign.pk, scheduled_date=today()
    )
    assert foreign_occ is not None
    habit_services.record_habit_checkin(
        clinic_id=world.clinic.pk, occurrence_id=foreign_occ.pk, status="completed"
    )
    html = (
        login(world.clinic, world.admin).get(_url("habit_list", world)).content.decode()
    )
    assert "Registros recentes de hábitos" in html
    assert "Feito" in html and "Parcial" in html and "Pulado" in html
    assert "Feito: 1" in html
    assert "Hábito de outra pessoa" not in html
    assert "Sem registros" not in html


def test_empty_states_say_that_the_patient_sees_nothing() -> None:
    world = build_world()
    admin = login(world.clinic, world.admin)
    assert (
        "O paciente não vê nada nesta área do app"
        in admin.get(_url("care_plan_list", world)).content.decode()
    )
    assert (
        "O paciente não vê nada nesta área do app"
        in admin.get(_url("habit_list", world)).content.decode()
    )


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


def _every_screen(world: World) -> list[str]:
    """Cria dados que exercitam cada tela e devolve as URLs (GET) a renderizar."""
    third = make_patient(world.clinic, world.admin, name="Caio Reis")

    def url(name: str, patient: PatientProfile, *extra: Any) -> str:
        return reverse(f"routines:{name}", args=[patient.pk, *extra])

    me = world.patient
    visible = make_medication(world)
    suspended = make_medication(world, medication_name="Zolpidem")
    suspend_prescribed_medication(
        clinic_id=world.clinic.pk,
        patient_profile_id=me.pk,
        medication_id=suspended.pk,
        actor_id=world.admin.pk,
    )
    for hours, status in ((42, "taken"), (35, "late"), (56, "omitted")):
        record_medication_dose(
            clinic_id=world.clinic.pk,
            medication_id=visible.pk,
            scheduled_time=timezone.now() - timedelta(hours=hours),
            status=status,
        )
    draft = make_plan(world)
    paused = make_plan(world, status="active")  # o paciente a pausa e pede revisão
    care_plan_services.respond_to_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=paused.pk,
        decision=PatientResponseChoice.PAUSED,
        patient_notes="Preciso de uma pausa.",
    )
    care_plan_services.respond_to_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=paused.pk,
        decision=PatientResponseChoice.REVIEW_REQUESTED,
    )
    awaiting = make_plan(world, patient=third, status="pending_signature")
    active = make_plan(world, patient=world.other_patient, status="active")
    live = make_habit(world, title="Caminhar ao ar livre")
    habit_services.pause_habit(
        clinic_id=world.clinic.pk,
        habit_id=make_habit(world, title="Alongar o corpo").pk,
    )
    habit_services.archive_habit(
        clinic_id=world.clinic.pk,
        habit_id=make_habit(world, title="Ler um capítulo").pk,
    )
    occurrence = habit_services.ensure_habit_occurrence(
        clinic_id=world.clinic.pk, habit_id=live.pk, scheduled_date=today()
    )
    assert occurrence is not None
    habit_services.record_habit_checkin(
        clinic_id=world.clinic.pk, occurrence_id=occurrence.pk
    )
    return [
        url("medication_list", me),
        url("medication_create", me),
        url("medication_edit", me, visible.pk),
        url("medication_stop", me, visible.pk),
        url("medication_stop", me, suspended.pk),
        url("medication_resume", me, suspended.pk),
        url("care_plan_list", me),
        url("care_plan_create", me),
        url("care_plan_detail", me, draft.pk),
        url("care_plan_detail", me, paused.pk),
        url("care_plan_edit", me, draft.pk),
        url("care_plan_submit", me, draft.pk),
        url("care_plan_resume", me, paused.pk),
        url("care_plan_close", me, paused.pk),
        url("care_plan_detail", third, awaiting.pk),
        url("care_plan_reopen", third, awaiting.pk),
        url("care_plan_sign", third, awaiting.pk),
        url("care_plan_pause", world.other_patient, active.pk),
        url("habit_list", me),
        url("habit_create", me),
        url("habit_edit", me, live.pk),
        url("habit_pause", me, live.pk),
        url("habit_archive", me, live.pk),
    ]


@pytest.mark.parametrize(
    ("language", "marker"),
    [("en", "Care plans"), ("es", "Planes de cuidado")],
)
def test_every_staff_screen_renders_in_english_and_spanish(
    language: str, marker: str
) -> None:
    world = build_world()
    urls = _every_screen(world)
    client = login(world.clinic, world.admin)
    portuguese = _catalog("pt_BR")
    target = _catalog(language)
    translated = {
        msgid for msgid in portuguese if target.get(msgid) not in {None, msgid}
    }
    user_data = {
        "Sertralina",
        "Zolpidem",
        "Dra. Helena Prado",
        "Plano de retorno gradual",
        "Retomar a rotina com apoio da equipe.",
        "Raciocínio clínico interno do caso.",
        "Evitar esforço intenso.",
        "Caminhada leve",
        "Diária",
        "Vinte minutos ao ar livre.",
        "Beber água",
        "Um copo ao acordar.",
        "Alongar o corpo",
        "Ler um capítulo",
        "Caminhar ao ar livre",
        "Preciso de uma pausa.",
        "Tomar após as refeições.",
        "Ana Souza",
        "Bia Lima",
        "Caio Reis",
    }
    for url in urls:
        response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200, url  # cada tela é de fato exercitada
        html = response.content.decode()
        leaked = (_text_nodes(html) & translated) - user_data
        assert not leaked, f"{url}: sem tradução em {language}: {sorted(leaked)}"
    listing = client.get(urls[6], HTTP_ACCEPT_LANGUAGE=language).content.decode()
    assert marker in listing


def test_review_screen_and_messages_follow_the_active_language() -> None:
    world = build_world()
    client = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    review = client.post(url, medication_form(), HTTP_ACCEPT_LANGUAGE="en")
    html = review.content.decode()
    assert "Review before publishing" in html
    assert "Nothing has been saved yet." in html
    assert "Publish in the patient app" in html
    posted = hidden_fields(html) | {"action": "publish", "confirm": "on"}
    done = client.post(url, posted, HTTP_ACCEPT_LANGUAGE="en", follow=True)
    assert "Medication published in the patient app." in done.content.decode()
    spanish = client.post(url, medication_form(), HTTP_ACCEPT_LANGUAGE="es")
    assert "Revisar antes de publicar" in spanish.content.decode()
    assert "Publicar en la app del paciente" in spanish.content.decode()


def test_validation_messages_follow_the_active_language() -> None:
    world = build_world()
    client = login(world.clinic, world.admin)
    url = _url("medication_create", world)
    bad = medication_form(schedule_times="25:00")
    english = client.post(url, bad, HTTP_ACCEPT_LANGUAGE="en").content.decode()
    assert "Invalid time: 25:00. Use HH:MM, for example 08:00." in english
    spanish = client.post(url, bad, HTTP_ACCEPT_LANGUAGE="es").content.decode()
    assert "Horario no válido: 25:00. Use HH:MM, por ejemplo 08:00." in spanish
    unsafe = medication_form(instructions="Duplique a dose se esquecer.")
    assert (
        "cannot be published in the app"
        in client.post(url, unsafe, HTTP_ACCEPT_LANGUAGE="en").content.decode()
    )
    hint = client.get(url, HTTP_ACCEPT_LANGUAGE="en").content.decode()
    assert "time zone (America/Sao_Paulo)" in hint
