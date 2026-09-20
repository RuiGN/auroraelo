"""HTML real e identidades sintéticas: prévias não simulam cuidado ou gravação."""

from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.translation import override

from psychiatry.models import PsychiatricPatientProfile
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

UNAVAILABLE_ROUTES = (
    "crisis_protocol",
    "inpatient_beds",
    "telepsychiatry",
    "anamnesis",
    "twelve_steps_anamnesis",
    "addiction_dashboard",
    "mobile_connected",
    "mobile_b2c",
)


class RenderedPage(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.in_main = False
        self.main_tags = []
        self.main_text = []
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "main":
            self.in_main = True
        if self.in_main:
            self.main_tags.append((tag, attrs))

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False

    def handle_data(self, data):
        if self.in_main:
            self.main_text.append(data)

    @property
    def text(self):
        return " ".join(" ".join(self.main_text).split())


@pytest.fixture
def identities():
    clinic = ClinicFactory.create()
    actors = {}
    for role in ("therapist", "patient", "clinic_admin"):
        actor = UserFactory.create()
        ClinicMembershipFactory.create(clinic=clinic, user=actor, role=role)
        actors[role] = actor
    return clinic, actors


def make_profile(clinic=None, user=None, name="Paciente Sintético Conectado"):
    marker = uuid4().hex[:10]
    return PsychiatricPatientProfile.objects.create(
        clinic=clinic,
        user=user,
        full_name=name,
        cpf=marker,
        date_of_birth=date(1990, 1, 1),
        record_number=marker,
        phone="",
    )


def get_page(identities, route, *, role="therapist"):
    clinic, actors = identities
    client = Client(enforce_csrf_checks=True)
    client.force_login(actors[role])
    with override("pt-br"):
        response = client.get(
            reverse(f"psychiatry:{route}"),
            headers={"X-Clinic-ID": str(clinic.pk)},
        )
    assert response.status_code == 200, response.content
    html = response.content.decode()
    return html, RenderedPage(html)


@pytest.mark.parametrize("route", UNAVAILABLE_ROUTES)
def test_nonintegrated_surfaces_do_not_collect_or_simulate_care(identities, route):
    clinic, actors = identities
    if route == "mobile_connected":
        make_profile(clinic, actors["patient"])
    html, page = get_page(
        identities,
        route,
        role="patient" if route == "mobile_connected" else "therapist",
    )
    assert "Indisponível nesta interface" in page.text
    assert "Esta página não grava dados nem envia notificações." in page.text
    assert not any(
        tag in {"form", "input", "textarea", "select"}
        or (tag == "button" and "disabled" not in attrs)
        for tag, attrs in page.main_tags
    )
    assert not any(key.startswith("on") for _, attrs in page.tags for key in attrs)
    assert all(
        attrs.get("src", "").startswith("/static/")
        for tag, attrs in page.tags
        if tag == "script"
    )
    for claim in (
        "0800770356",
        "24h",
        "Mariana",
        "Marcelo",
        "Roberto Carlos",
        "Escitalopram",
        "Quetiapina",
        "E2EE",
        "TCLE Ativo",
        "MP notificado",
        "Intervenção médica preventiva acionada",
        "22 Pacientes",
        "26 Pacientes",
        "78 Dias Limpos",
        "14 Dias Seguidos",
        "29,90",
        "Alívio instantâneo",
        "showToast",
        "navigateStep",
        "fetch(",
        "Sincronizado no Redis",
    ):
        assert claim not in html
    assert reverse("workspace_vertical") in html
    assert "192 (SAMU)" in html and "188 (CVV)" in html


@pytest.fixture
def authorized_profile(identities):
    from consents.services import record_consent_manifestation
    from people.models import CareRelationship
    from tests.test_versioned_consents import publish_document

    clinic, actors = identities
    document = publish_document(clinic=clinic, actor=actors["clinic_admin"])
    record_consent_manifestation(
        clinic_id=clinic.pk,
        actor=actors["patient"],
        subject_id=actors["patient"].pk,
        document_id=document.pk,
        decision="accepted",
        request_id=uuid4(),
    )
    CareRelationship.infrastructure_objects.create(
        clinic=clinic,
        therapist=actors["therapist"],
        patient=actors["patient"],
        valid_from=date.today(),
    )
    return make_profile(
        clinic, actors["patient"], "Pessoa Sintética <script>erro</script>"
    )


@pytest.mark.parametrize(
    "route", ("patients", "addiction_dashboard", "mobile_connected")
)
def test_authorized_identity_is_rendered_without_demo_or_foreign_data(
    identities, authorized_profile, route
):
    from psychiatry.models import AddictionProfile

    clinic, actors = identities
    foreign = make_profile(
        ClinicFactory.create(), actors["patient"], "Outro Tenant Sintético"
    )
    legacy = make_profile(name="Legado Sem Vínculo Sintético")
    unrelated = make_profile(clinic, UserFactory.create(), "Sem Relação Sintético")
    for patient in (authorized_profile, foreign, legacy, unrelated):
        AddictionProfile.objects.create(patient=patient)
    html, page = get_page(
        identities,
        route,
        role="patient" if route == "mobile_connected" else "therapist",
    )
    assert authorized_profile.full_name in page.text
    assert "&lt;script&gt;erro&lt;/script&gt;" in html
    assert "<script>erro</script>" not in html
    for excluded in (foreign, legacy, unrelated):
        assert excluded.full_name not in html
        assert excluded.cpf not in html
    for demo in ("Mariana", "Roberto", "Camila", "128 pacientes", "PRON-2026-0842"):
        assert demo not in html
    assert not any(
        tag in {"form", "input", "textarea", "select", "button"}
        for tag, _ in page.main_tags
    )


@pytest.mark.parametrize("route", ("patients", "addiction_dashboard"))
def test_empty_authorized_list_is_not_replaced_by_demo(identities, route):
    html, page = get_page(identities, route)
    assert "Nenhum paciente disponível para este acesso." in page.text
    for demo in (
        "Mariana",
        "Roberto",
        "Camila",
        "128 pacientes",
        "Execute o comando de seed",
    ):
        assert demo not in html


@pytest.mark.parametrize("route", ("patients", "addiction_dashboard"))
def test_care_revocation_removes_identity_from_rendered_html(
    identities, authorized_profile, route
):
    from people.models import CareRelationship
    from psychiatry.models import AddictionProfile

    clinic, actors = identities
    AddictionProfile.objects.create(patient=authorized_profile)
    _, before = get_page(identities, route)
    assert authorized_profile.full_name in before.text
    CareRelationship.infrastructure_objects.filter(
        clinic=clinic, therapist=actors["therapist"], patient=actors["patient"]
    ).update(is_active=False)
    _, after = get_page(identities, route)
    assert authorized_profile.full_name not in after.text
    assert "Nenhum paciente disponível para este acesso." in after.text


@pytest.mark.parametrize("language", ("pt-br", "en", "es"))
def test_every_psychiatry_template_renders_with_local_assets(
    identities, language, tmp_path
):
    """Inclui os três shells fora do ownership, sem editá-los."""
    from django.conf import settings
    from django.contrib.staticfiles import finders
    from django.template.loader import render_to_string
    from django.test import RequestFactory

    clinic, actors = identities
    request = RequestFactory().get("/psiquiatria/")
    request.user = actors["therapist"]
    request.clinic = clinic
    request.session = {}
    templates = sorted(
        (Path(settings.BASE_DIR) / "psychiatry/templates/psychiatry").glob("*.html")
    )
    assert len(templates) == 12
    for template in templates:
        with override(language):
            html = render_to_string(
                f"psychiatry/{template.name}",
                {"patients": [], "profiles": [], "monitoring_active": False},
                request=request,
            )
        page = RenderedPage(html)
        assert f'lang="{language}"' in html
        assert len([tag for tag, _ in page.tags if tag == "main"]) == 1
        assert "{%" not in html and "{{" not in html
        for tag, attrs in page.tags:
            if tag in {"script", "img", "link"}:
                asset = attrs.get("src") or attrs.get("href")
                if asset:
                    assert asset.startswith("/static/"), asset
                    assert finders.find(asset.removeprefix("/static/")), asset
        (tmp_path / template.name).write_text(html, encoding="utf-8")
