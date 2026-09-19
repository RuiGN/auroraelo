"""Behavioral regressions for the Mindcare workspace presentation."""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory


class WorkspaceLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_workspace = False
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id") == "workspace-shortcuts":
            self.in_workspace = True
        if self.in_workspace and tag == "a" and attributes.get("href"):
            self.links.add(str(attributes["href"]))


@pytest.mark.django_db
@pytest.mark.parametrize("layout", ("workspace_vertical", "workspace_detached"))
@pytest.mark.parametrize("role", ("patient", "therapist", "clinic_admin"))
def test_workspace_offers_role_scoped_actions_without_demo_metrics(
    client: Client, role: str, layout: str
) -> None:
    user = UserFactory.create()
    clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(user=user, clinic=clinic, role=role)
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    response = client.get(reverse(layout))
    assert response.status_code == 200
    html = response.content.decode()
    parser = WorkspaceLinks()
    parser.feed(html)
    assert reverse("account_sessions") in parser.links
    assert (reverse("journal_list") in parser.links) == (role == "patient")
    assert (reverse("therapist_dashboard") in parser.links) == (role == "therapist")
    assert (reverse("clinic_setup") in parser.links) == (role == "clinic_admin")
    for demo in (
        "Módulos disponíveis",
        "Configurações pendentes",
        "Registros sintéticos",
        "RGN Terapêutica",
    ):
        assert demo not in html
    assert response.context_data is not None
    assert "summary_cards" not in response.context_data
    assert "activity_table" not in response.context_data
    assert "Mindcare" in html


@pytest.mark.django_db
def test_switching_clinic_changes_workspace_actions(client: Client) -> None:
    user = UserFactory.create()
    patient_clinic = ClinicFactory.create()
    admin_clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(user=user, clinic=patient_clinic, role="patient")
    ClinicMembershipFactory.create(user=user, clinic=admin_clinic, role="clinic_admin")
    client.force_login(user)
    for clinic, expected in (
        (patient_clinic, "journal_list"),
        (admin_clinic, "clinic_setup"),
    ):
        session = client.session
        session["active_clinic_id"] = str(clinic.pk)
        session.save()
        response = client.get(reverse("workspace_vertical"))
        parser = WorkspaceLinks()
        parser.feed(response.content.decode())
        assert reverse(expected) in parser.links
        other = "clinic_setup" if expected == "journal_list" else "journal_list"
        assert reverse(other) not in parser.links
