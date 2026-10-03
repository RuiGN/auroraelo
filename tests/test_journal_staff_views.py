"""Telas da equipe para o diário e os check-ins que o paciente compartilha."""

from __future__ import annotations

import gettext as gettext_module
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from uuid import UUID, uuid4

import pytest
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import reverse
from django.utils import timezone, translation

from accounts.models import User
from audit.models import AuditAction, AuditEvent
from clinics.models import Clinic, ClinicMembership
from journal import selectors as journal_selectors
from journal import services as journal_services
from journal.models import DailyCheckIn, JournalAccessRequest, JournalEntry
from people import services as people_services
from people.models import PatientProfile
from tests.aftercare_support import PatientLogin, build_stage, make_patient_login
from tests.factories import ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

SHARED_TEXT = "Texto-compartilhado-pelo-paciente"
GRANTED_TEXT = "Texto-liberado-a-pedido"
YELLOW_TEXT = "Texto-que-pede-confirmacao"
PRIVATE_TEXT = "Texto-privado-do-paciente"
NOTE_TEXT = "Observacao-escrita-no-checkin"


@dataclass
class Scene:
    """Clínica sintética com terapeuta vinculado, par sem vínculo e outra clínica."""

    clinic: Clinic
    admin: User
    staff: User
    therapist: User
    peer: User
    patient: PatientLogin
    peer_patient: PatientLogin
    other_clinic: Clinic
    other_therapist: User
    other_patient: PatientLogin


def _link(
    clinic: Clinic,
    admin: User,
    therapist: User,
    profile: PatientProfile,
    *,
    valid_from: date | None = None,
    valid_until: date | None = None,
) -> None:
    people_services.create_patient_care_relationship(
        clinic_id=clinic.pk,
        actor=admin,
        therapist_id=therapist.pk,
        patient_profile_id=profile.pk,
        function="primary_therapist",
        valid_from=valid_from or timezone.localdate() - timedelta(days=1),
        valid_until=valid_until,
        request_id=uuid4(),
    )


def build_scene() -> Scene:
    stage = build_stage()
    peer = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=stage.clinic, user=peer, role=ClinicMembership.Role.THERAPIST
    )
    other_therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=stage.other_clinic,
        user=other_therapist,
        role=ClinicMembership.Role.THERAPIST,
    )
    patient = make_patient_login(stage.clinic, stage.admin, name="Paciente Um")
    peer_patient = make_patient_login(stage.clinic, stage.admin, name="Paciente Dois")
    other_patient = make_patient_login(
        stage.other_clinic, stage.other_admin, name="Paciente Fora"
    )
    _link(stage.clinic, stage.admin, stage.therapist, patient.profile)
    _link(stage.clinic, stage.admin, peer, peer_patient.profile)
    _link(stage.other_clinic, stage.other_admin, other_therapist, other_patient.profile)
    return Scene(
        clinic=stage.clinic,
        admin=stage.admin,
        staff=stage.staff,
        therapist=stage.therapist,
        peer=peer,
        patient=patient,
        peer_patient=peer_patient,
        other_clinic=stage.other_clinic,
        other_therapist=other_therapist,
        other_patient=other_patient,
    )


def _client(clinic: Clinic, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


def _entry(
    login: PatientLogin,
    visibility: str,
    context: str,
    *,
    mood: int = 2,
    emotions: list[str] | None = None,
    triggers: str = "",
    days_ago: int = 0,
) -> JournalEntry:
    entry = journal_services.create_journal_entry(
        clinic_id=login.clinic.pk,
        actor=login.user,
        patient_profile_id=login.profile.pk,
        mood=mood,
        emotions=emotions if emotions is not None else ["anxiety"],
        intensity=3,
        context=context,
        triggers=triggers,
        reactions="",
        strategies="",
        visibility=visibility,
        request_id=uuid4(),
    )
    if days_ago:
        JournalEntry.infrastructure_objects.filter(pk=entry.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
        entry.refresh_from_db()
    return entry


def _ask(scene: Scene, entry: JournalEntry, *, days: int = 30) -> JournalAccessRequest:
    return journal_services.request_journal_entry_access(
        clinic_id=scene.clinic.pk,
        therapist=scene.therapist,
        journal_entry_id=entry.pk,
        purpose="Revisar o episódio com o paciente",
        expires_at=timezone.now() + timedelta(days=days),
        request_id=uuid4(),
    )


def _answer(
    scene: Scene,
    request: JournalAccessRequest,
    *,
    approved: bool,
    expires_at: Any = None,
) -> JournalAccessRequest:
    return journal_services.respond_journal_entry_access_request(
        clinic_id=scene.clinic.pk,
        actor=scene.patient.user,
        access_request_id=request.pk,
        approved=approved,
        expires_at=expires_at,
        request_id=uuid4(),
    )


def _checkin(
    scene: Scene,
    day: date,
    answers: dict[str, object],
    *,
    visibility: str = JournalEntry.Visibility.SHAREABLE,
    draft: bool = False,
    login: PatientLogin | None = None,
) -> DailyCheckIn:
    owner = login or scene.patient
    questionnaire = journal_services.ensure_default_checkin_questionnaire(
        clinic_id=owner.clinic.pk
    )
    return DailyCheckIn.infrastructure_objects.create(
        clinic_id=owner.clinic.pk,
        patient_profile_id=owner.profile.pk,
        author_id=owner.user.pk,
        questionnaire=questionnaire,
        questionnaire_version=questionnaire.version,
        date=day,
        period="daily",
        answers=answers,
        visibility=visibility,
        is_draft=draft,
        submitted_at=None if draft else timezone.now(),
    )


def _scores(base: int = 3, **overrides: object) -> dict[str, object]:
    keys = journal_selectors.CHECKIN_SCALE_KEYS
    return {key: base for key in keys} | overrides


def _day(moment: datetime) -> str:
    """Data local como a tela mostra (dd/mm/aaaa em português)."""
    return timezone.localtime(moment).strftime("%d/%m/%Y")


def _diary_url(profile: PatientProfile) -> str:
    return reverse("journal:patient_diary", args=[profile.pk])


def _checkins_url(profile: PatientProfile) -> str:
    return reverse("journal:patient_checkins", args=[profile.pk])


def _request_url(profile: PatientProfile, entry_id: UUID) -> str:
    return reverse("journal:access_request_create", args=[profile.pk, entry_id])


def _audit(scene: Scene, resource_type: str, action: str | None = None) -> int:
    queryset = AuditEvent.infrastructure_objects.filter(
        clinic_id=scene.clinic.pk, resource_type=resource_type
    )
    if action is not None:
        queryset = queryset.filter(action=action)
    return queryset.count()


# ── Acesso e autorização ────────────────────────────────────────────────────


def test_anonymous_users_are_sent_to_login() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    client = Client()
    for url in (
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
        _request_url(scene.patient.profile, entry.pk),
    ):
        response = client.get(url)
        assert (
            response.status_code == 302 and "/accounts/login/" in response["Location"]
        )


def test_linked_therapist_opens_both_screens_without_caching() -> None:
    scene = build_scene()
    client = _client(scene.clinic, scene.therapist)
    for url in (
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
    ):
        response = client.get(url)
        assert response.status_code == 200
        assert response["Cache-Control"] == "private, no-store"
        html = response.content.decode()
        assert 'class="ae-navbar"' in html
        assert "Paciente Um" in html


def test_access_request_page_is_never_cached() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    response = _client(scene.clinic, scene.therapist).get(
        _request_url(scene.patient.profile, entry.pk)
    )
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("role", ["admin", "staff"])
def test_clinic_admin_and_administrative_staff_have_no_diary_access(role: str) -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _entry(scene.patient, "shareable", SHARED_TEXT)
    user = scene.admin if role == "admin" else scene.staff
    client = _client(scene.clinic, user)
    for url in (
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
        _request_url(scene.patient.profile, entry.pk),
    ):
        assert client.get(url).status_code == 403, url
    assert (
        client.post(
            _request_url(scene.patient.profile, entry.pk),
            {"purpose": "Preciso ver este registro", "validity_days": "30"},
        ).status_code
        == 403
    )
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 0
    assert _audit(scene, "journal_diary") == 0


def test_therapist_without_an_active_link_is_denied_everywhere() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _entry(scene.patient, "shareable", SHARED_TEXT)
    client = _client(scene.clinic, scene.peer)  # terapeuta da clínica, outro paciente
    for url in (
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
        _request_url(scene.patient.profile, entry.pk),
    ):
        assert client.get(url).status_code == 403, url
    response = client.post(
        _request_url(scene.patient.profile, entry.pk),
        {"purpose": "Preciso ver este registro", "validity_days": "30"},
    )
    assert response.status_code == 403
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 0
    assert _audit(scene, "journal_diary") == 0
    assert _audit(scene, "daily_checkin_series") == 0


def test_an_ended_care_link_closes_the_diary() -> None:
    scene = build_scene()
    peer_profile = scene.peer_patient.profile
    _link(
        scene.clinic,
        scene.admin,
        scene.therapist,
        peer_profile,
        valid_from=timezone.localdate() - timedelta(days=30),
        valid_until=timezone.localdate() - timedelta(days=1),
    )
    _entry(scene.peer_patient, "shareable", SHARED_TEXT)
    client = _client(scene.clinic, scene.therapist)
    assert client.get(_diary_url(peer_profile)).status_code == 403
    assert client.get(_checkins_url(peer_profile)).status_code == 403


def test_other_clinic_ids_and_sessions_never_open_the_diary() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    foreign_entry = _entry(scene.other_patient, "confirmation_required", YELLOW_TEXT)

    # terapeuta da outra clínica, com a própria clínica ativa, usando o ID do paciente
    outsider = _client(scene.other_clinic, scene.other_therapist)
    for url in (
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
        _request_url(scene.patient.profile, entry.pk),
    ):
        assert outsider.get(url).status_code == 403, url

    # o terapeuta vinculado não alcança a outra clínica trocando a sessão
    wrong_session = _client(scene.other_clinic, scene.therapist)
    assert wrong_session.get(_diary_url(scene.patient.profile)).status_code == 403

    # ID de registro de outra clínica na rota do próprio paciente
    mine = _client(scene.clinic, scene.therapist)
    assert (
        mine.get(_request_url(scene.patient.profile, foreign_entry.pk)).status_code
        == 403
    )
    assert (
        mine.post(
            _request_url(scene.patient.profile, foreign_entry.pk),
            {"purpose": "Preciso ver este registro", "validity_days": "30"},
        ).status_code
        == 403
    )
    assert JournalAccessRequest.infrastructure_objects.count() == 0


def test_unknown_patient_answers_like_an_unlinked_one() -> None:
    scene = build_scene()
    client = _client(scene.clinic, scene.therapist)
    unknown = uuid4()
    assert (
        client.get(reverse("journal:patient_diary", args=[unknown])).status_code == 403
    )
    assert (
        client.get(reverse("journal:patient_checkins", args=[unknown])).status_code
        == 403
    )
    assert (
        client.get(
            reverse("journal:access_request_create", args=[unknown, uuid4()])
        ).status_code
        == 403
    )


def test_patient_web_sessions_are_refused() -> None:
    scene = build_scene()
    _entry(scene.patient, "shareable", SHARED_TEXT)
    client = _client(scene.clinic, scene.patient.user)
    assert client.get(_diary_url(scene.patient.profile)).status_code == 403
    assert client.get(_checkins_url(scene.patient.profile)).status_code == 403


def test_pages_reject_unsafe_methods() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    client = _client(scene.clinic, scene.therapist)
    assert client.post(_diary_url(scene.patient.profile)).status_code == 405
    assert client.post(_checkins_url(scene.patient.profile)).status_code == 405
    assert client.put(_request_url(scene.patient.profile, entry.pk)).status_code == 405
    # abrir o formulário (GET) nunca grava nada
    client.get(_request_url(scene.patient.profile, entry.pk))
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 0


# ── Diário: o que aparece e o que nunca aparece ─────────────────────────────


def test_diary_lists_only_what_the_patient_shared() -> None:
    scene = build_scene()
    shared = _entry(
        scene.patient,
        "shareable",
        SHARED_TEXT,
        mood=1,
        emotions=["anxiety", "hope"],
        triggers="Gatilho-informado",
    )
    _entry(scene.patient, "private", PRIVATE_TEXT, emotions=["anger"])
    _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _entry(scene.peer_patient, "shareable", "Texto-de-outro-paciente")
    _entry(scene.other_patient, "shareable", "Texto-de-outra-clinica")

    html = (
        _client(scene.clinic, scene.therapist)
        .get(_diary_url(scene.patient.profile))
        .content.decode()
    )

    assert SHARED_TEXT in html
    assert "Humor: Muito mal (1/5)" in html
    assert "Ansiedade" in html and "Esperança" in html
    assert "Gatilho-informado" in html
    assert "Compartilhado pelo paciente" in html
    assert _day(shared.created_at) in html
    for hidden in (
        PRIVATE_TEXT,
        YELLOW_TEXT,
        "Texto-de-outro-paciente",
        "Texto-de-outra-clinica",
    ):
        assert hidden not in html


def test_private_records_leave_no_trace_not_even_a_count() -> None:
    scene = build_scene()
    _entry(scene.patient, "shareable", SHARED_TEXT)
    client = _client(scene.clinic, scene.therapist)
    before = client.get(_diary_url(scene.patient.profile)).content.decode()
    for _ in range(3):
        _entry(scene.patient, "private", PRIVATE_TEXT, emotions=["anger"])
    after = client.get(_diary_url(scene.patient.profile)).content.decode()

    def stable(html: str) -> str:
        # só o conteúdo e o CSRF mudam entre leituras; o resto tem de ser idêntico
        return re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', "", html)

    assert stable(before) == stable(after)
    assert PRIVATE_TEXT not in after
    assert "Raiva" not in after
    assert "Vermelho" not in after and "Privado" not in after


def test_confirmation_records_show_only_date_and_request_state() -> None:
    scene = build_scene()
    entry = _entry(
        scene.patient,
        "confirmation_required",
        YELLOW_TEXT,
        mood=1,
        emotions=["fear"],
        triggers="Gatilho-amarelo",
        days_ago=2,
    )
    response = _client(scene.clinic, scene.therapist).get(
        _diary_url(scene.patient.profile)
    )
    html = response.content.decode()
    assert "Registros que pedem confirmação" in html
    assert _day(entry.created_at) in html
    assert _request_url(scene.patient.profile, entry.pk) in html
    assert "Nenhum pedido feito" in html
    for hidden in (YELLOW_TEXT, "Gatilho-amarelo", "Medo", "Muito mal"):
        assert hidden not in html


def test_period_filter_and_pagination() -> None:
    scene = build_scene()
    _entry(scene.patient, "shareable", "Registro-antigo", days_ago=100)
    for number in range(12):
        _entry(scene.patient, "shareable", f"Registro-recente-{number:02d}")
    client = _client(scene.clinic, scene.therapist)
    url = _diary_url(scene.patient.profile)

    first = client.get(url).content.decode()
    assert first.count("Registro-recente-") == 10
    assert "Registro-antigo" not in first
    assert "Página 1 de 2" in first
    second = client.get(url, {"periodo": "30d", "pagina": "2"}).content.decode()
    assert second.count("Registro-recente-") == 2
    everything = client.get(url, {"periodo": "todos", "pagina": "2"}).content.decode()
    assert "Registro-antigo" in everything
    # valores inválidos voltam ao padrão em vez de quebrar
    assert client.get(url, {"periodo": "x", "pagina": "x"}).status_code == 200


# ── Pedido de acesso ────────────────────────────────────────────────────────


def test_request_form_is_prefilled_with_safe_defaults_and_hides_content() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT, days_ago=1)
    response = _client(scene.clinic, scene.therapist).get(
        _request_url(scene.patient.profile, entry.pk)
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "Pedir acesso a um registro" in html
    assert "Finalidade do pedido" in html
    assert 'value="30" selected' in html
    assert "Quem decide é o paciente" in html
    assert YELLOW_TEXT not in html
    assert _day(entry.created_at) in html


def test_therapist_requests_access_and_sees_the_pending_state() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    client = _client(scene.clinic, scene.therapist)
    before = _audit(scene, "journal_access_request", AuditAction.CREATE)

    response = client.post(
        _request_url(scene.patient.profile, entry.pk),
        {"purpose": "Retomar o episódio na sessão", "validity_days": "15"},
    )

    assert response.status_code == 302
    assert response["Location"] == _diary_url(scene.patient.profile)
    saved = JournalAccessRequest.objects.for_clinic(scene.clinic.pk).get()
    assert saved.status == JournalAccessRequest.Status.PENDING
    assert saved.therapist_id == scene.therapist.pk
    assert saved.journal_entry_id == entry.pk
    assert saved.patient_profile_id == scene.patient.profile.pk
    assert saved.purpose == "Retomar o episódio na sessão"
    assert saved.expires_at is not None
    assert (
        timedelta(days=14, hours=23)
        < saved.expires_at - timezone.now()
        < timedelta(days=15, minutes=1)
    )
    # auditado com o terapeuta como ator e o pedido como recurso
    event = AuditEvent.infrastructure_objects.get(
        clinic_id=scene.clinic.pk,
        resource_type="journal_access_request",
        resource_id=str(saved.pk),
    )
    assert event.action == AuditAction.CREATE and event.actor_id == scene.therapist.pk
    assert _audit(scene, "journal_access_request", AuditAction.CREATE) == before + 1

    page = client.get(response["Location"])
    html = page.content.decode()
    assert "Aguardando resposta do paciente" in html
    assert "Retomar o episódio na sessão" in html
    assert _request_url(scene.patient.profile, entry.pk) not in html  # sem repetir
    assert YELLOW_TEXT not in html


def test_form_errors_are_shown_and_nothing_is_saved() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    client = _client(scene.clinic, scene.therapist)
    for data in (
        {"purpose": "curto", "validity_days": "30"},
        {"purpose": "Finalidade suficientemente longa", "validity_days": "9999"},
        {"validity_days": "30"},
    ):
        response = client.post(_request_url(scene.patient.profile, entry.pk), data)
        assert response.status_code == 200
        assert "Revise os campos indicados" in response.content.decode()
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 0


@pytest.mark.parametrize("visibility", ["private", "shareable"])
def test_only_confirmation_required_records_can_be_requested(visibility: str) -> None:
    scene = build_scene()
    entry = _entry(scene.patient, visibility, PRIVATE_TEXT)
    client = _client(scene.clinic, scene.therapist)
    url = _request_url(scene.patient.profile, entry.pk)
    assert client.get(url).status_code == 403
    assert (
        client.post(
            url, {"purpose": "Preciso ver este registro", "validity_days": "30"}
        ).status_code
        == 403
    )
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 0


def test_a_record_of_another_patient_cannot_be_requested_through_this_route() -> None:
    scene = build_scene()
    entry = _entry(scene.peer_patient, "confirmation_required", YELLOW_TEXT)
    client = _client(scene.clinic, scene.therapist)
    # o ID do registro é de um paciente que o terapeuta não acompanha
    assert client.get(_request_url(scene.patient.profile, entry.pk)).status_code == 403
    assert (
        client.get(_request_url(scene.peer_patient.profile, entry.pk)).status_code
        == 403
    )
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 0


def test_a_pending_request_is_not_repeated() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _ask(scene, entry)
    client = _client(scene.clinic, scene.therapist)
    url = _request_url(scene.patient.profile, entry.pk)
    assert client.get(url).status_code == 302
    response = client.post(
        url,
        {"purpose": "Mais um pedido para o mesmo registro", "validity_days": "30"},
        follow=True,
    )
    assert "Já existe um pedido aguardando a resposta do paciente." in (
        response.content.decode()
    )
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 1


def test_approved_request_releases_the_content_until_it_ends() -> None:
    scene = build_scene()
    entry = _entry(
        scene.patient,
        "confirmation_required",
        GRANTED_TEXT,
        mood=2,
        emotions=["sadness"],
        triggers="Gatilho-liberado",
    )
    request = _ask(scene, entry)
    client = _client(scene.clinic, scene.therapist)
    assert (
        GRANTED_TEXT
        not in client.get(_diary_url(scene.patient.profile)).content.decode()
    )

    until = timezone.now() + timedelta(days=10)
    _answer(scene, request, approved=True, expires_at=until)
    html = client.get(_diary_url(scene.patient.profile)).content.decode()

    assert GRANTED_TEXT in html and "Gatilho-liberado" in html
    assert "Liberado a pedido" in html
    assert _day(until) in html
    assert "Aprovado pelo paciente" in html
    # liberado, o registro sai da lista de pendentes de confirmação
    assert "Registros que pedem confirmação" not in html
    assert _request_url(scene.patient.profile, entry.pk) not in html


def test_expired_access_closes_the_content_and_allows_a_new_request() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", GRANTED_TEXT)
    request = _answer(scene, _ask(scene, entry), approved=True)
    JournalAccessRequest.infrastructure_objects.filter(pk=request.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    client = _client(scene.clinic, scene.therapist)

    html = client.get(_diary_url(scene.patient.profile)).content.decode()

    assert GRANTED_TEXT not in html
    assert "Expirado" in html
    assert _request_url(scene.patient.profile, entry.pk) in html
    # um novo pedido é aceito e o antigo continua no histórico
    response = client.post(
        _request_url(scene.patient.profile, entry.pk),
        {"purpose": "Renovar o acesso ao registro", "validity_days": "7"},
    )
    assert response.status_code == 302
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 2


def test_a_lapsed_pending_request_reads_as_expired() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    request = _ask(scene, entry)
    JournalAccessRequest.infrastructure_objects.filter(pk=request.pk).update(
        expires_at=timezone.now() - timedelta(hours=1)
    )
    diary = journal_selectors.therapist_patient_diary(
        clinic_id=scene.clinic.pk,
        therapist_id=scene.therapist.pk,
        patient_profile_id=scene.patient.profile.pk,
        period="todos",
    )
    assert [row.state for row in diary.requests] == ["expired"]
    assert [(row.state, row.can_request) for row in diary.confirmation] == [
        ("expired", True)
    ]


def test_refusal_is_final_for_the_team() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _answer(scene, _ask(scene, entry), approved=False)
    client = _client(scene.clinic, scene.therapist)
    html = client.get(_diary_url(scene.patient.profile)).content.decode()
    assert "Recusado pelo paciente" in html
    assert YELLOW_TEXT not in html
    assert _request_url(scene.patient.profile, entry.pk) not in html
    response = client.post(
        _request_url(scene.patient.profile, entry.pk),
        {"purpose": "Insistir no mesmo registro", "validity_days": "30"},
        follow=True,
    )
    assert "O paciente recusou este pedido." in response.content.decode()
    assert JournalAccessRequest.objects.for_clinic(scene.clinic.pk).count() == 1


def test_going_private_again_revokes_the_release_at_once() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", GRANTED_TEXT)
    _answer(scene, _ask(scene, entry), approved=True)
    client = _client(scene.clinic, scene.therapist)
    assert (
        GRANTED_TEXT in client.get(_diary_url(scene.patient.profile)).content.decode()
    )

    journal_services.revoke_journal_entry_sharing(
        clinic_id=scene.clinic.pk,
        actor=scene.patient.user,
        journal_entry_id=entry.pk,
        request_id=uuid4(),
    )
    html = client.get(_diary_url(scene.patient.profile)).content.decode()
    assert GRANTED_TEXT not in html
    assert "Revogado" in html  # o histórico do pedido continua
    # o registro voltou a ser privado: não aparece nem como pendente de confirmação
    assert "Registros que pedem confirmação" not in html
    assert _request_url(scene.patient.profile, entry.pk) not in html
    assert client.get(_request_url(scene.patient.profile, entry.pk)).status_code == 403


def test_a_release_is_personal_to_the_therapist_who_asked() -> None:
    scene = build_scene()
    _link(scene.clinic, scene.admin, scene.peer, scene.patient.profile)
    entry = _entry(scene.patient, "confirmation_required", GRANTED_TEXT)
    _answer(scene, _ask(scene, entry), approved=True)

    asker = _client(scene.clinic, scene.therapist).get(
        _diary_url(scene.patient.profile)
    )
    colleague = _client(scene.clinic, scene.peer).get(_diary_url(scene.patient.profile))
    assert GRANTED_TEXT in asker.content.decode()
    assert colleague.status_code == 200
    colleague_html = colleague.content.decode()
    assert GRANTED_TEXT not in colleague_html
    assert "Aprovado pelo paciente" not in colleague_html  # sem o pedido do colega
    assert _request_url(scene.patient.profile, entry.pk) in colleague_html


# ── Check-ins ───────────────────────────────────────────────────────────────


def test_checkin_series_uses_only_shared_submitted_answers_in_the_window() -> None:
    scene = build_scene()
    today = timezone.localdate()
    _checkin(scene, today, _scores(2, anxiety=5, notes=NOTE_TEXT))
    _checkin(scene, today - timedelta(days=1), _scores(4, anxiety=3))
    _checkin(scene, today - timedelta(days=2), _scores(1), visibility="private")
    _checkin(
        scene, today - timedelta(days=3), _scores(1), visibility="confirmation_required"
    )
    _checkin(scene, today - timedelta(days=4), _scores(1), draft=True)
    _checkin(scene, today - timedelta(days=20), _scores(5))  # fora da janela de 14 dias
    _checkin(scene, today, _scores(1), login=scene.peer_patient)

    series = journal_selectors.therapist_patient_checkin_series(
        clinic_id=scene.clinic.pk,
        therapist_id=scene.therapist.pk,
        patient_profile_id=scene.patient.profile.pk,
        days=14,
    )

    assert series.shared_count == 2
    assert [row.day for row in series.rows] == [today, today - timedelta(days=1)]
    assert len(series.days) == 14 and series.days[-1] == today
    by_key = {item.key: item for item in series.questions}
    assert tuple(by_key) == journal_selectors.CHECKIN_SCALE_KEYS and len(by_key) == 7
    anxiety = by_key["anxiety"]
    assert anxiety.answered == 2 and anxiety.average == 4.0 and anxiety.latest == 5
    assert anxiety.scores[-1] == 5 and anxiety.scores[-2] == 3
    assert all(score is None for score in anxiety.scores[:-2])
    assert by_key["energy"].average == 3.0 and by_key["energy"].latest == 2

    wide = journal_selectors.therapist_patient_checkin_series(
        clinic_id=scene.clinic.pk,
        therapist_id=scene.therapist.pk,
        patient_profile_id=scene.patient.profile.pk,
        days=30,
    )
    assert wide.shared_count == 3


def test_checkin_scores_outside_the_scale_read_as_unanswered() -> None:
    scene = build_scene()
    today = timezone.localdate()
    _checkin(
        scene,
        today,
        _scores(
            3, anxiety=9, sadness="x", irritability=True, energy=None, motivation="4"
        ),
    )
    series = journal_selectors.therapist_patient_checkin_series(
        clinic_id=scene.clinic.pk,
        therapist_id=scene.therapist.pk,
        patient_profile_id=scene.patient.profile.pk,
    )
    by_key = {item.key: item for item in series.questions}
    for key in ("anxiety", "sadness", "irritability", "energy"):
        assert by_key[key].answered == 0 and by_key[key].average is None
    assert by_key["motivation"].latest == 4 and by_key["general_state"].latest == 3


def test_checkin_screen_shows_the_series_and_hides_notes_and_private_days() -> None:
    scene = build_scene()
    today = timezone.localdate()
    _checkin(scene, today, _scores(2, anxiety=5, notes=NOTE_TEXT))
    _checkin(scene, today - timedelta(days=1), _scores(4, anxiety=3))
    _checkin(
        scene, today - timedelta(days=2), _scores(1, sadness=5), visibility="private"
    )
    client = _client(scene.clinic, scene.therapist)

    response = client.get(_checkins_url(scene.patient.profile))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'data-testid="stat-shared">2<' in html
    for label in (
        "Estado geral",
        "Ansiedade",
        "Tristeza ou desânimo",
        "Irritabilidade",
        "Disposição e energia",
        "Qualidade do sono",
        "Motivação",
    ):
        assert label in html
    assert html.count('role="img"') == 7  # um gráfico de barras por pergunta
    assert "ae-bars__bar--v5" in html and "ae-bars__bar--v3" in html
    assert "Valores por dia" in html and "Evolução por pergunta" in html
    assert NOTE_TEXT not in html
    assert "ae-table-wrap" in html
    # a série de 30 dias é aceita e valores inválidos voltam ao padrão
    assert (
        client.get(_checkins_url(scene.patient.profile), {"dias": "30"}).status_code
        == 200
    )
    assert (
        client.get(_checkins_url(scene.patient.profile), {"dias": "abc"}).status_code
        == 200
    )
    assert (
        client.get(_checkins_url(scene.patient.profile), {"dias": "9999"}).status_code
        == 200
    )


def test_checkin_screen_without_shared_checkins_says_so() -> None:
    scene = build_scene()
    _checkin(scene, timezone.localdate(), _scores(1), visibility="private")
    html = (
        _client(scene.clinic, scene.therapist)
        .get(_checkins_url(scene.patient.profile))
        .content.decode()
    )
    assert "Nenhum check-in compartilhado neste período." in html
    assert 'role="img"' not in html


def test_selectors_refuse_unlinked_and_non_therapist_callers() -> None:
    scene = build_scene()
    arguments: dict[str, Any] = {
        "clinic_id": scene.clinic.pk,
        "patient_profile_id": scene.patient.profile.pk,
    }
    for caller in (scene.peer, scene.admin, scene.staff, scene.patient.user):
        with pytest.raises(PermissionDenied):
            journal_selectors.therapist_patient_diary(
                therapist_id=caller.pk, **arguments
            )
        with pytest.raises(PermissionDenied):
            journal_selectors.therapist_patient_checkin_series(
                therapist_id=caller.pk, **arguments
            )
        with pytest.raises(PermissionDenied):
            journal_selectors.therapist_confirmation_entry(
                therapist_id=caller.pk, entry_id=uuid4(), **arguments
            )
        with pytest.raises(PermissionDenied):
            journal_services.record_staff_diary_read(
                clinic_id=scene.clinic.pk,
                actor=caller,
                patient_profile_id=scene.patient.profile.pk,
                request_id=uuid4(),
            )
        with pytest.raises(PermissionDenied):
            journal_services.record_staff_checkins_read(
                clinic_id=scene.clinic.pk,
                actor=caller,
                patient_profile_id=scene.patient.profile.pk,
                request_id=uuid4(),
            )
    assert _audit(scene, "journal_diary") == 0


# ── Auditoria ───────────────────────────────────────────────────────────────


def test_every_read_is_audited_without_content() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "shareable", SHARED_TEXT)
    _checkin(scene, timezone.localdate(), _scores(3, notes=NOTE_TEXT))
    client = _client(scene.clinic, scene.therapist)

    client.get(_diary_url(scene.patient.profile))
    client.get(_diary_url(scene.patient.profile), {"periodo": "todos"})
    client.get(_checkins_url(scene.patient.profile))

    diary_events = AuditEvent.infrastructure_objects.filter(
        clinic_id=scene.clinic.pk, resource_type="journal_diary"
    )
    assert diary_events.count() == 2
    for event in diary_events:
        assert event.action == AuditAction.VIEW
        assert event.actor_id == scene.therapist.pk
        assert event.resource_id == str(scene.patient.profile.pk)
        assert event.outcome == "success"
    checkin_event = AuditEvent.infrastructure_objects.get(
        clinic_id=scene.clinic.pk, resource_type="daily_checkin_series"
    )
    assert checkin_event.action == AuditAction.VIEW
    assert checkin_event.resource_id == str(scene.patient.profile.pk)
    # nada do conteúdo vai para a trilha
    dump = repr(
        list(
            AuditEvent.infrastructure_objects.filter(clinic_id=scene.clinic.pk).values()
        )
    )
    for secret in (SHARED_TEXT, NOTE_TEXT):
        assert secret not in dump
    assert entry.pk is not None


def test_denied_reads_and_requests_write_no_audit_trail() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    client = _client(scene.clinic, scene.peer)
    client.get(_diary_url(scene.patient.profile))
    client.get(_checkins_url(scene.patient.profile))
    client.post(
        _request_url(scene.patient.profile, entry.pk),
        {"purpose": "Preciso ver este registro", "validity_days": "30"},
    )
    assert _audit(scene, "journal_diary") == 0
    assert _audit(scene, "daily_checkin_series") == 0
    assert _audit(scene, "journal_access_request") == 0


def test_the_patients_answer_to_a_request_is_audited_as_consent() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", GRANTED_TEXT)
    request = _ask(scene, entry)
    _answer(scene, request, approved=True)
    assert _audit(scene, "journal_entry", AuditAction.CONSENT_ACCEPT) == 1
    journal_services.revoke_journal_entry_sharing(
        clinic_id=scene.clinic.pk,
        actor=scene.patient.user,
        journal_entry_id=entry.pk,
        request_id=uuid4(),
    )
    assert _audit(scene, "journal_entry", AuditAction.CONSENT_REVOKE) == 1


# ── CSP e estrutura ─────────────────────────────────────────────────────────


def test_pages_are_csp_safe_and_load_only_local_assets() -> None:
    scene = build_scene()
    entry = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _entry(scene.patient, "shareable", SHARED_TEXT)
    _checkin(scene, timezone.localdate(), _scores(3))
    client = _client(scene.clinic, scene.therapist)
    for url in (
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
        _request_url(scene.patient.profile, entry.pk),
    ):
        html = client.get(url).content.decode()
        assert re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) == []
        assert not re.search(r"(?:src|href)=[\"']https?://", html)
        assert "fonts.googleapis.com" not in html
        assert "ae-journal.css" in html
        assert re.search(r"<table", html) is None or "ae-table-wrap" in html


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


def _seed_every_state(scene: Scene) -> list[str]:
    """Registros e pedidos em todos os estados, mais check-ins; devolve as URLs."""
    _entry(
        scene.patient,
        "shareable",
        SHARED_TEXT,
        emotions=["frustration", "hope"],
        triggers="Gatilho-informado",
    )
    granted = _entry(scene.patient, "confirmation_required", GRANTED_TEXT)
    _answer(scene, _ask(scene, granted), approved=True)
    refused = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _answer(scene, _ask(scene, refused), approved=False)
    pending = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    _ask(scene, pending)
    lapsed = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    stale = _answer(scene, _ask(scene, lapsed), approved=True)
    JournalAccessRequest.infrastructure_objects.filter(pk=stale.pk).update(
        expires_at=timezone.now() - timedelta(days=1)
    )
    fresh = _entry(scene.patient, "confirmation_required", YELLOW_TEXT)
    today = timezone.localdate()
    for offset in range(5):
        _checkin(scene, today - timedelta(days=offset), _scores(1 + offset % 5))
    return [
        _diary_url(scene.patient.profile),
        _checkins_url(scene.patient.profile),
        _request_url(scene.patient.profile, fresh.pk),
    ]


@pytest.mark.parametrize(
    ("language", "marker", "emotions"),
    [
        ("en", "Diary of Paciente Um", ("Frustration", "Hope")),
        ("es", "Diario de Paciente Um", ("Frustración", "Esperanza")),
    ],
)
def test_every_screen_renders_in_english_and_spanish(
    language: str, marker: str, emotions: tuple[str, str]
) -> None:
    scene = build_scene()
    urls = _seed_every_state(scene)
    client = _client(scene.clinic, scene.therapist)
    portuguese = _catalog("pt_BR")
    target = _catalog(language)
    untranslated = {
        msgid for msgid in portuguese if target.get(msgid) not in {None, msgid}
    }
    user_data = {
        "Paciente Um",
        SHARED_TEXT,
        GRANTED_TEXT,
        "Gatilho-informado",
        "Revisar o episódio com o paciente",
    }
    for url in urls:
        response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200, url
        html = response.content.decode()
        leaked = (_text_nodes(html) & untranslated) - user_data
        assert not leaked, f"{url}: sem tradução em {language}: {sorted(leaked)}"
    diary = client.get(urls[0], HTTP_ACCEPT_LANGUAGE=language).content.decode()
    assert marker in diary
    assert "Diário de Paciente Um" not in diary
    # os rótulos de emoção vêm do catálogo: um msgid trocado aparece aqui
    for label in emotions:
        assert f">{label}<" in diary


def test_emotion_labels_read_correctly_in_portuguese() -> None:
    from journal.presentation import emotion_labels

    codes = [code for code, _label in JournalEntry.Emotion.choices]
    with translation.override("pt-br"):
        assert emotion_labels(codes) == [
            str(label) for _code, label in JournalEntry.Emotion.choices
        ]


def test_state_labels_cover_every_request_state() -> None:
    from journal.presentation import ACCESS_STATE_LABELS, ACCESS_STATE_TONES

    expected = {
        journal_selectors.ACCESS_NONE,
        journal_selectors.ACCESS_PENDING,
        journal_selectors.ACCESS_GRANTED,
        journal_selectors.ACCESS_REJECTED,
        journal_selectors.ACCESS_REVOKED,
        journal_selectors.ACCESS_EXPIRED,
    }
    assert set(ACCESS_STATE_LABELS) == expected == set(ACCESS_STATE_TONES)
