"""Telas web do concierge: acesso por papel, isolamento por URL e fluxos completos."""

from __future__ import annotations

import gettext as gettext_module
import re
from datetime import timedelta
from html.parser import HTMLParser
from uuid import uuid4

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clinics.models import Clinic
from concierge import services
from concierge.models import (
    AftercareContact,
    CommunicationRule,
    ConciergeLog,
    Discharge,
    FamilyContact,
    FamilyRequest,
)
from people.models import PatientProfile
from tests.aftercare_support import Stage, build_stage, make_patient

pytestmark = pytest.mark.django_db


def _client(clinic: Clinic, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


def _discharge(stage: Stage, days_ago: int = 3) -> tuple[PatientProfile, Discharge]:
    patient = make_patient(stage.clinic, stage.admin)
    discharge = services.register_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        discharge_date=timezone.localdate() - timedelta(days=days_ago),
        request_id=uuid4(),
    )
    return patient, discharge


def _family(
    stage: Stage, patient: PatientProfile, consent: bool = True
) -> FamilyContact:
    return services.add_family_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        full_name="Marta Exemplo",
        relationship="Mãe",
        phone="+55 81 0000-0001",
        consent_to_contact=consent,
        consent_note="Termo assinado" if consent else "",
        request_id=uuid4(),
    )


# ── Acesso ──────────────────────────────────────────────────────────────────

GET_ROUTES = [
    "concierge:dashboard",
    "concierge:contact_queue",
    "concierge:discharge_list",
    "concierge:discharge_create",
    "concierge:log_list",
    "concierge:request_list",
    "concierge:rule_list",
    "concierge:rule_edit",
]


def test_anonymous_users_are_sent_to_login() -> None:
    client = Client()
    for name in GET_ROUTES:
        response = client.get(reverse(name))
        assert (
            response.status_code == 302 and "/accounts/login/" in response["Location"]
        )


@pytest.mark.parametrize("route", [r for r in GET_ROUTES if r != "concierge:rule_edit"])
def test_staff_and_admin_can_open_every_read_screen(route: str) -> None:
    stage = build_stage()
    for user in (stage.staff, stage.admin):
        response = _client(stage.clinic, user).get(reverse(route))
        assert response.status_code == 200, (route, user.pk)
        html = response.content.decode()
        assert 'class="ae-navbar"' in html  # layout do design system


@pytest.mark.parametrize("route", GET_ROUTES)
def test_therapists_have_no_access_to_concierge_screens(route: str) -> None:
    stage = build_stage()
    response = _client(stage.clinic, stage.therapist).get(reverse(route))
    assert response.status_code == 403


def test_rule_editing_is_reserved_to_the_clinic_admin() -> None:
    stage = build_stage()
    assert (
        _client(stage.clinic, stage.staff)
        .get(reverse("concierge:rule_edit"))
        .status_code
        == 403
    )
    assert (
        _client(stage.clinic, stage.admin)
        .get(reverse("concierge:rule_edit"))
        .status_code
        == 200
    )


def test_navigation_shows_the_aftercare_menu_only_to_authorized_roles() -> None:
    stage = build_stage()
    staff_html = (
        _client(stage.clinic, stage.staff)
        .get(reverse("concierge:dashboard"))
        .content.decode()
    )
    assert 'id="menu-posalta"' in staff_html
    assert reverse("concierge:contact_queue") in staff_html
    therapist_home = _client(stage.clinic, stage.therapist).get(
        reverse("workspace_vertical")
    )
    assert reverse("concierge:dashboard") not in therapist_home.content.decode()
    admin_home = _client(stage.clinic, stage.admin).get(reverse("workspace_vertical"))
    assert (
        reverse("concierge:dashboard") in admin_home.content.decode()
    )  # menu lateral legado


def test_pages_are_csp_safe_and_load_only_local_assets() -> None:
    stage = build_stage()
    _discharge(stage)
    client = _client(stage.clinic, stage.staff)
    for route in (
        "concierge:dashboard",
        "concierge:discharge_list",
        "concierge:contact_queue",
    ):
        html = client.get(reverse(route)).content.decode()
        assert re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) == []
        assert not re.search(r"(?:src|href)=[\"']https?://", html)
        assert "fonts.googleapis.com" not in html


# ── Isolamento: IDs de outra clínica nunca abrem ────────────────────────────


def test_foreign_ids_in_urls_are_denied() -> None:
    stage = build_stage()
    patient, discharge = _discharge(stage)
    family = _family(stage, patient)
    contact = AftercareContact.objects.for_clinic(stage.clinic.pk).first()
    assert contact is not None
    family_request = services.register_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        kind="call_me",
        description="Pedido de rotina",
        request_id=uuid4(),
    )
    log = services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Contato de rotina.",
        request_id=uuid4(),
    )
    outsider = _client(stage.other_clinic, stage.other_admin)
    urls = [
        reverse("concierge:discharge_detail", args=[discharge.pk]),
        reverse("concierge:discharge_cancel", args=[discharge.pk]),
        reverse("concierge:contact_complete", args=[contact.pk]),
        reverse("concierge:contact_reschedule", args=[contact.pk]),
        reverse("concierge:contact_missed", args=[contact.pk]),
        reverse("concierge:patient_detail", args=[patient.pk]),
        reverse("concierge:family_create", args=[patient.pk]),
        reverse("concierge:log_create", args=[patient.pk]),
        reverse("concierge:request_create", args=[patient.pk]),
        reverse("concierge:family_edit", args=[family.pk]),
        reverse("concierge:family_consent", args=[family.pk]),
        reverse("concierge:log_correct", args=[log.pk]),
        reverse("concierge:request_forward", args=[family_request.pk]),
        reverse("concierge:request_resolve", args=[family_request.pk]),
        reverse("concierge:request_cancel", args=[family_request.pk]),
    ]
    for url in urls:
        assert outsider.get(url).status_code == 403, url
    posts = [
        reverse("concierge:family_deactivate", args=[family.pk]),
    ]
    for url in posts:
        assert outsider.post(url).status_code == 403, url
    family.refresh_from_db()
    assert family.is_active  # nada mudou


def test_dangerous_actions_do_not_run_on_get() -> None:
    stage = build_stage()
    patient, _ = _discharge(stage)
    family = _family(stage, patient)
    client = _client(stage.clinic, stage.staff)
    assert (
        client.get(reverse("concierge:family_deactivate", args=[family.pk])).status_code
        == 405
    )
    family.refresh_from_db()
    assert family.is_active


# ── Fluxos ──────────────────────────────────────────────────────────────────


def test_staff_registers_a_discharge_and_sees_the_generated_schedule() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin, name="Ana Souza")
    client = _client(stage.clinic, stage.staff)
    page = client.get(reverse("concierge:discharge_create")).content.decode()
    assert "Ana Souza" in page
    response = client.post(
        reverse("concierge:discharge_create"),
        {
            "patient": str(patient.pk),
            "discharge_date": timezone.localdate().isoformat(),
            "notes": "",
        },
    )
    assert response.status_code == 302
    discharge = Discharge.objects.for_clinic(stage.clinic.pk).get()
    detail = client.get(response["Location"]).content.decode()
    assert "Ligação" in detail and "Visita presencial" in detail
    assert detail.count("ae-badge") >= 3
    assert discharge.contacts.count() == 3
    # a mesma paciente deixa de aparecer como opção
    assert (
        "Ana Souza"
        not in client.get(reverse("concierge:discharge_create")).content.decode()
    )


def test_discharge_form_rejects_a_future_date_with_a_visible_error() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    client = _client(stage.clinic, stage.staff)
    response = client.post(
        reverse("concierge:discharge_create"),
        {
            "patient": str(patient.pk),
            "discharge_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
        },
    )
    assert response.status_code == 200
    assert "não pode ser futura" in response.content.decode()
    assert not Discharge.objects.for_clinic(stage.clinic.pk).exists()


def test_complete_and_reschedule_a_contact_through_the_forms() -> None:
    stage = build_stage()
    patient, discharge = _discharge(stage, days_ago=8)
    family = _family(stage, patient)
    client = _client(stage.clinic, stage.staff)
    call = AftercareContact.objects.for_clinic(stage.clinic.pk).get(
        discharge=discharge, kind="call", day_after_discharge=7
    )
    visit = AftercareContact.objects.for_clinic(stage.clinic.pk).get(
        discharge=discharge, kind="visit"
    )
    form = client.get(
        reverse("concierge:contact_complete", args=[call.pk])
    ).content.decode()
    assert (
        "Conseguiu falar" in form and "Visita realizada" not in form
    )  # só desfechos de ligação
    response = client.post(
        reverse("concierge:contact_complete", args=[call.pk]),
        {"outcome": "reached", "family_contact": str(family.pk), "notes": "Tudo bem."},
    )
    assert response.status_code == 302
    call.refresh_from_db()
    assert call.status == "done"
    assert (
        ConciergeLog.objects.for_clinic(stage.clinic.pk)
        .filter(aftercare_contact=call)
        .exists()
    )
    response = client.post(
        reverse("concierge:contact_reschedule", args=[visit.pk]),
        {
            "new_due_date": (timezone.localdate() + timedelta(days=9)).isoformat(),
            "reason": "Pediu outro dia",
        },
    )
    assert response.status_code == 302
    visit.refresh_from_db()
    assert visit.reschedule_count == 1


def test_family_contact_and_consent_flow() -> None:
    stage = build_stage()
    patient, _ = _discharge(stage)
    client = _client(stage.clinic, stage.staff)
    url = reverse("concierge:family_create", args=[patient.pk])
    bad = client.post(
        url,
        {
            "full_name": "Pedro Exemplo",
            "relationship": "Irmão",
            "phone": "",
            "email": "",
            "consent_to_contact": "on",
            "consent_note": "",
        },
    )
    assert (
        bad.status_code == 200
        and "Informe ao menos um telefone ou e-mail" in bad.content.decode()
    )
    ok = client.post(
        url,
        {
            "full_name": "Pedro Exemplo",
            "relationship": "Irmão",
            "phone": "+55 81 0000-0002",
            "email": "pedro@example.test",
        },
    )
    assert ok.status_code == 302
    family = FamilyContact.objects.for_clinic(stage.clinic.pk).get()
    assert not family.consent_to_contact
    detail = client.get(
        reverse("concierge:patient_detail", args=[patient.pk])
    ).content.decode()
    assert "Sem autorização" in detail and "Pedro Exemplo" in detail
    # sem autorização, o familiar não aparece como opção de registro
    log_form = client.get(
        reverse("concierge:log_create", args=[patient.pk])
    ).content.decode()
    assert "Pedro Exemplo" not in log_form
    client.post(
        reverse("concierge:family_consent", args=[family.pk]),
        {"decision": "grant", "note": "Termo assinado hoje"},
    )
    family.refresh_from_db()
    assert family.can_be_contacted
    log_form = client.get(
        reverse("concierge:log_create", args=[patient.pk])
    ).content.decode()
    assert "Pedro Exemplo" in log_form


def test_log_and_request_flow_with_correction() -> None:
    stage = build_stage()
    patient, _ = _discharge(stage)
    family = _family(stage, patient)
    client = _client(stage.clinic, stage.staff)
    response = client.post(
        reverse("concierge:log_create", args=[patient.pk]),
        {
            "family_contact": str(family.pk),
            "channel": "call",
            "direction": "outbound",
            "occurred_at": "",
            "summary": "Combinamos o horário de visita.",
        },
    )
    assert response.status_code == 302
    log = ConciergeLog.objects.for_clinic(stage.clinic.pk).get()
    page = client.get(
        reverse("concierge:patient_detail", args=[patient.pk])
    ).content.decode()
    assert "Combinamos o horário de visita." in page
    assert reverse("concierge:log_correct", args=[log.pk]) in page
    client.post(
        reverse("concierge:log_correct", args=[log.pk]),
        {"new_summary": "Combinamos o horário de domingo.", "reason": "Dia errado"},
    )
    assert ConciergeLog.objects.for_clinic(stage.clinic.pk).count() == 2
    page = client.get(
        reverse("concierge:patient_detail", args=[patient.pk])
    ).content.decode()
    assert "Combinamos o horário de visita." in page  # o original permanece visível
    assert "correção de um registro anterior" in page

    created = client.post(
        reverse("concierge:request_create", args=[patient.pk]),
        {
            "family_contact": str(family.pk),
            "kind": "bring_item",
            "description": "Trazer o carregador.",
        },
    )
    assert created.status_code == 302
    family_request = FamilyRequest.objects.for_clinic(stage.clinic.pk).get()
    listing = client.get(reverse("concierge:request_list")).content.decode()
    assert "A família ainda não foi contatada." in listing
    assert reverse("concierge:request_resolve", args=[family_request.pk]) not in listing
    client.post(
        reverse("concierge:request_forward", args=[family_request.pk]),
        {"channel": "call", "summary": "Passei o pedido para a Marta."},
    )
    listing = client.get(reverse("concierge:request_list")).content.decode()
    assert reverse("concierge:request_resolve", args=[family_request.pk]) in listing
    client.post(
        reverse("concierge:request_resolve", args=[family_request.pk]),
        {"outcome": "fulfilled", "note": "Entregue no sábado."},
    )
    family_request.refresh_from_db()
    assert family_request.status == "fulfilled"


def test_admin_edits_the_rule_and_new_discharges_follow_it() -> None:
    stage = build_stage()
    client = _client(stage.clinic, stage.admin)
    data = {"name": "Régua em 3 etapas"}
    for index in range(8):
        data[f"step_{index}_role"] = "administrative_staff"
    data.update(
        {
            "step_0_kind": "call",
            "step_0_day": "3",
            "step_1_kind": "call",
            "step_1_day": "10",
            "step_2_kind": "visit",
            "step_2_day": "20",
        }
    )
    response = client.post(reverse("concierge:rule_edit"), data)
    assert response.status_code == 302
    rule = CommunicationRule.objects.for_clinic(stage.clinic.pk).get(is_active=True)
    assert rule.name == "Régua em 3 etapas"
    page = client.get(reverse("concierge:rule_list")).content.decode()
    assert "Régua em 3 etapas" in page and ">20<" in page
    # linha incompleta gera erro visível
    bad = dict(data, step_3_kind="call", step_3_day="")
    response = client.post(reverse("concierge:rule_edit"), bad)
    assert (
        response.status_code == 200
        and "Preencha o tipo e os dias da etapa 4" in response.content.decode()
    )


def test_discharge_cancel_and_missed_screens() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=10)
    client = _client(stage.clinic, stage.staff)
    overdue = AftercareContact.objects.for_clinic(stage.clinic.pk).get(
        discharge=discharge, kind="call", day_after_discharge=7
    )
    detail = client.get(
        reverse("concierge:discharge_detail", args=[discharge.pk])
    ).content.decode()
    assert (
        reverse("concierge:contact_missed", args=[overdue.pk]) in detail
    )  # atrasado oferece "Não realizado"
    client.post(
        reverse("concierge:contact_missed", args=[overdue.pk]),
        {"notes": "Número desligado"},
    )
    overdue.refresh_from_db()
    assert overdue.status == "missed"
    client.post(
        reverse("concierge:discharge_cancel", args=[discharge.pk]),
        {"reason": "Registrada por engano"},
    )
    discharge.refresh_from_db()
    assert discharge.status == "canceled"


def test_dashboard_shows_counts_and_family_consent_warning() -> None:
    stage = build_stage()
    _discharge(stage, days_ago=10)  # ligação de 7 dias atrasada
    html = (
        _client(stage.clinic, stage.staff)
        .get(reverse("concierge:dashboard"))
        .content.decode()
    )
    assert 'data-testid="stat-overdue">1<' in html
    assert "ainda não tem familiar autorizado" in html


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
    """Cria dados que exercitam todas as telas e devolve as URLs (GET) a renderizar."""
    patient, discharge = _discharge(stage, days_ago=10)
    family = _family(stage, patient)
    services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Combinamos o horário.",
        request_id=uuid4(),
    )
    family_request = services.register_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        kind="bring_item",
        description="Trazer o livro.",
        request_id=uuid4(),
    )
    contact = discharge.contacts.order_by("due_date").first()
    assert contact is not None
    log = ConciergeLog.objects.for_clinic(stage.clinic.pk).get()
    return [
        reverse("concierge:dashboard"),
        reverse("concierge:contact_queue"),
        reverse("concierge:discharge_list"),
        reverse("concierge:discharge_create"),
        reverse("concierge:discharge_detail", args=[discharge.pk]),
        reverse("concierge:discharge_cancel", args=[discharge.pk]),
        reverse("concierge:contact_complete", args=[contact.pk]),
        reverse("concierge:contact_reschedule", args=[contact.pk]),
        reverse("concierge:contact_missed", args=[contact.pk]),
        reverse("concierge:patient_detail", args=[patient.pk]),
        reverse("concierge:family_create", args=[patient.pk]),
        reverse("concierge:family_edit", args=[family.pk]),
        reverse("concierge:family_consent", args=[family.pk]),
        reverse("concierge:log_create", args=[patient.pk]),
        reverse("concierge:log_correct", args=[log.pk]),
        reverse("concierge:log_list"),
        reverse("concierge:request_create", args=[patient.pk]),
        reverse("concierge:request_list"),
        reverse("concierge:request_forward", args=[family_request.pk]),
        reverse("concierge:rule_list"),
        reverse("concierge:rule_edit"),
    ]


@pytest.mark.parametrize(
    ("language", "navigation", "dashboard_title"),
    [
        ("en", "Contact queue", "Post-discharge follow-up"),
        ("es", "Cola de contactos", "Seguimiento posterior al alta"),
    ],
)
def test_every_concierge_screen_renders_in_english_and_spanish(
    language: str, navigation: str, dashboard_title: str
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
    # dados gravados: o nome da régua padrão é salvo na criação (renomeável)
    user_data = {
        "Marta Exemplo",
        "Mãe",
        "Combinamos o horário.",
        "Trazer o livro.",
        "Régua padrão pós-alta",
    }
    for url in urls:
        response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200, url
        html = response.content.decode()
        leaked = (_text_nodes(html) & untranslated) - user_data
        assert not leaked, f"{url}: sem tradução em {language}: {sorted(leaked)}"
    dashboard = client.get(urls[0], HTTP_ACCEPT_LANGUAGE=language).content.decode()
    assert navigation in dashboard and dashboard_title in dashboard
    assert f'<html lang="{language}"' in dashboard or f'lang="{language}"' in dashboard


def test_validation_messages_follow_the_active_language() -> None:
    stage = build_stage()
    client = _client(stage.clinic, stage.admin)
    data = {"name": "Régua"} | {
        f"step_{i}_role": "administrative_staff" for i in range(8)
    }
    data |= {"step_0_kind": "call", "step_0_day": ""}
    english = client.post(
        reverse("concierge:rule_edit"), data, HTTP_ACCEPT_LANGUAGE="en"
    ).content.decode()
    assert "Fill in the type and days for step 1." in english
    spanish = client.post(
        reverse("concierge:rule_edit"), data, HTTP_ACCEPT_LANGUAGE="es"
    ).content.decode()
    assert "Complete el tipo y los días de la etapa 1." in spanish
    portuguese = client.post(reverse("concierge:rule_edit"), data).content.decode()
    assert "Preencha o tipo e os dias da etapa 1." in portuguese
