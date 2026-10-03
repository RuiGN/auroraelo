"""Acceptance tests for PRD 8.6.1 and 8.6.2 journal entries and UI experience."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TypedDict
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.utils import timezone

from accounts.models import User
from accounts.services import accept_invitation
from audit.models import AuditEvent
from clinics.models import Clinic, ClinicMembership
from journal import selectors as journal_selectors
from journal import services as journal_services
from journal.models import (
    CONTEXT_MAX_LENGTH,
    DETAIL_MAX_LENGTH,
    JournalAccessRequest,
    JournalEntry,
)
from people import services as people_services
from people.models import PatientProfile
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db


class PatientPayload(TypedDict):
    full_name: str
    social_name: str
    birth_date: date
    gender: str
    email: str
    phone: str
    language_code: str
    timezone_name: str
    accessibility_preferences: str
    address: dict[str, object]
    address_purpose: str
    emergency_contact: dict[str, object]
    emergency_contact_purpose: str


class EntryKwargs(TypedDict):
    mood: int
    emotions: list[str]
    intensity: int
    context: str
    triggers: str
    reactions: str
    strategies: str
    visibility: str


def _payload(email: str) -> PatientPayload:
    return {
        "full_name": "Paciente Exemplo",
        "social_name": "",
        "birth_date": date(1990, 1, 1),
        "gender": "undisclosed",
        "email": email,
        "phone": "",
        "language_code": "pt-BR",
        "timezone_name": "America/Sao_Paulo",
        "accessibility_preferences": "",
        "address": {},
        "address_purpose": "",
        "emergency_contact": {},
        "emergency_contact_purpose": "",
    }


def _linked_patient(
    clinic: Clinic, *, email: str = "um@example.test"
) -> tuple[User, User, PatientProfile]:
    administrator = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=administrator, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    profile = people_services.register_patient_profile(
        clinic_id=clinic.pk, actor=administrator, request_id=uuid4(), **_payload(email)
    )
    issued = people_services.issue_patient_invitation(
        clinic_id=clinic.pk,
        actor=administrator,
        patient_profile_id=profile.pk,
        expires_at=people_services.invitation_expiration_after(days=2),
        request_id=uuid4(),
    )
    user = accept_invitation(
        raw_token=issued.raw_token,
        password="senha-sintetica-longa-e-nao-reutilizavel",
        first_name="Paciente",
        last_name="Exemplo",
    )
    profile.refresh_from_db()
    return administrator, user, profile


def _entry_kwargs() -> EntryKwargs:
    return {
        "mood": JournalEntry.Mood.LOW,
        "emotions": ["anxiety", "sadness"],
        "intensity": 3,
        "context": "Dia difícil no trabalho.",
        "triggers": "Reunião tensa.",
        "reactions": "Coração acelerado.",
        "strategies": "Respirei fundo.",
        "visibility": JournalEntry.Visibility.PRIVATE,
    }


def _force_patient_client(client: Client, clinic: Clinic, user: User) -> None:
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()


# ---------------------------------------------------------------------------
# 8.6.1 Domain and Privacy Tests
# ---------------------------------------------------------------------------


def test_patient_creates_journal_entry_with_visibility() -> None:
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)

    entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **_entry_kwargs(),
    )

    assert isinstance(entry, JournalEntry)
    assert entry.author_id == user.pk
    assert entry.patient_profile_id == profile.pk
    assert entry.mood == JournalEntry.Mood.LOW
    assert entry.emotions == ["anxiety", "sadness"]
    assert entry.intensity == 3
    assert entry.visibility == JournalEntry.Visibility.PRIVATE


def test_journal_entry_rejects_invalid_intensity_and_emotion() -> None:
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)

    payload = _entry_kwargs()
    payload["intensity"] = 6
    with pytest.raises(ValidationError, match="intensidade"):
        journal_services.create_journal_entry(
            clinic_id=clinic.pk,
            actor=user,
            patient_profile_id=profile.pk,
            request_id=uuid4(),
            **payload,
        )

    payload = _entry_kwargs()
    payload["emotions"] = ["nao_existe"]
    with pytest.raises(ValidationError, match="emoções"):
        journal_services.create_journal_entry(
            clinic_id=clinic.pk,
            actor=user,
            patient_profile_id=profile.pk,
            request_id=uuid4(),
            **payload,
        )


def test_visibility_change_is_audited() -> None:
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)
    entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **_entry_kwargs(),
    )

    changed = journal_services.set_journal_entry_visibility(
        clinic_id=clinic.pk,
        actor=user,
        journal_entry_id=entry.pk,
        visibility=JournalEntry.Visibility.SHAREABLE,
        request_id=uuid4(),
    )

    assert changed.visibility == JournalEntry.Visibility.SHAREABLE
    assert AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk,
        resource_type="journal_entry",
        resource_id=str(entry.pk),
    ).exists()


def test_therapist_visible_entries_exclude_private_and_confirmation_required() -> None:
    clinic = ClinicFactory.create()
    administrator, user, profile = _linked_patient(clinic)
    therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    people_services.create_patient_care_relationship(
        clinic_id=clinic.pk,
        actor=administrator,
        therapist_id=therapist.pk,
        patient_profile_id=profile.pk,
        function="primary_therapist",
        valid_from=date.today(),
        valid_until=None,
        request_id=uuid4(),
    )
    shareable_payload = _entry_kwargs()
    shareable_payload["visibility"] = JournalEntry.Visibility.SHAREABLE
    shareable = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **shareable_payload,
    )
    yellow_payload = _entry_kwargs()
    yellow_payload["visibility"] = JournalEntry.Visibility.CONFIRMATION_REQUIRED
    journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **yellow_payload,
    )
    private_payload = _entry_kwargs()
    private_payload["visibility"] = JournalEntry.Visibility.PRIVATE
    journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **private_payload,
    )

    visible = journal_selectors.therapist_visible_journal_entries(
        clinic_id=clinic.pk, therapist_id=therapist.pk
    )

    assert [entry.pk for entry in visible] == [shareable.pk]


def test_journal_denies_other_patient_and_unlinked_therapist() -> None:
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)
    _administrator, other_user, _other_profile = _linked_patient(
        clinic, email="outro@example.test"
    )
    entry_payload = _entry_kwargs()
    entry_payload["visibility"] = JournalEntry.Visibility.SHAREABLE
    entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **entry_payload,
    )

    with pytest.raises(PermissionDenied):
        journal_services.set_journal_entry_visibility(
            clinic_id=clinic.pk,
            actor=other_user,
            journal_entry_id=entry.pk,
            visibility=JournalEntry.Visibility.PRIVATE,
            request_id=uuid4(),
        )

    unlinked_therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=unlinked_therapist, role=ClinicMembership.Role.THERAPIST
    )
    visible = journal_selectors.therapist_visible_journal_entries(
        clinic_id=clinic.pk, therapist_id=unlinked_therapist.pk
    )
    assert visible == []


def test_journal_entry_rejects_oversized_text() -> None:
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)

    payload = _entry_kwargs()
    payload["context"] = "x" * (CONTEXT_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        journal_services.create_journal_entry(
            clinic_id=clinic.pk,
            actor=user,
            patient_profile_id=profile.pk,
            request_id=uuid4(),
            **payload,
        )

    payload = _entry_kwargs()
    payload["triggers"] = "x" * (DETAIL_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        journal_services.create_journal_entry(
            clinic_id=clinic.pk,
            actor=user,
            patient_profile_id=profile.pk,
            request_id=uuid4(),
            **payload,
        )


def test_journal_update_limited_to_author() -> None:
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)
    _administrator, other_user, _other_profile = _linked_patient(
        clinic, email="outro@example.test"
    )
    entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        request_id=uuid4(),
        **_entry_kwargs(),
    )

    updated = journal_services.update_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        journal_entry_id=entry.pk,
        mood=JournalEntry.Mood.GOOD,
        emotions=["hope"],
        intensity=4,
        context="Atualizado pela própria autora.",
        triggers="",
        reactions="",
        strategies="",
        request_id=uuid4(),
    )

    assert updated.mood == JournalEntry.Mood.GOOD
    assert updated.context == "Atualizado pela própria autora."

    with pytest.raises(PermissionDenied):
        journal_services.update_journal_entry(
            clinic_id=clinic.pk,
            actor=other_user,
            journal_entry_id=entry.pk,
            mood=JournalEntry.Mood.GOOD,
            emotions=["hope"],
            intensity=4,
            context="Tentativa de outro usuário.",
            triggers="",
            reactions="",
            strategies="",
            request_id=uuid4(),
        )


def test_journal_cross_clinic_access_is_denied() -> None:
    clinic_a = ClinicFactory.create()
    _administrator_a, user_a, profile_a = _linked_patient(clinic_a)
    shareable_payload = _entry_kwargs()
    shareable_payload["visibility"] = JournalEntry.Visibility.SHAREABLE
    entry_a = journal_services.create_journal_entry(
        clinic_id=clinic_a.pk,
        actor=user_a,
        patient_profile_id=profile_a.pk,
        request_id=uuid4(),
        **shareable_payload,
    )

    clinic_b = ClinicFactory.create()
    _administrator_b, user_b, _profile_b = _linked_patient(
        clinic_b, email="b@example.test"
    )
    therapist_b = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic_b, user=therapist_b, role=ClinicMembership.Role.THERAPIST
    )

    # Patient B cannot read clinic A's journal.
    assert (
        journal_selectors.patient_journal_entries(clinic_id=clinic_a.pk, actor=user_b)
        == []
    )

    # Therapist B is denied clinic A's journal.
    with pytest.raises(PermissionDenied):
        journal_selectors.therapist_visible_journal_entries(
            clinic_id=clinic_a.pk, therapist_id=therapist_b.pk
        )

    # Patient B cannot mutate clinic A's entries.
    with pytest.raises(PermissionDenied):
        journal_services.set_journal_entry_visibility(
            clinic_id=clinic_a.pk,
            actor=user_b,
            journal_entry_id=entry_a.pk,
            visibility=JournalEntry.Visibility.PRIVATE,
            request_id=uuid4(),
        )

    with pytest.raises(PermissionDenied):
        journal_services.create_journal_entry(
            clinic_id=clinic_a.pk,
            actor=user_b,
            patient_profile_id=profile_a.pk,
            request_id=uuid4(),
            **shareable_payload,
        )


# ---------------------------------------------------------------------------
# 8.6.2 Forms and UI Acceptance Tests
# ---------------------------------------------------------------------------


def test_patient_journal_calendar_selector() -> None:
    """8.6.2.2: Test calendar data generator with legend, matrix, and summary."""
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)

    # Create entries on different dates
    journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        mood=JournalEntry.Mood.VERY_GOOD,
        emotions=["joy", "hope"],
        intensity=5,
        context="Dia maravilhoso com a família.",
        triggers="",
        reactions="",
        strategies="",
        visibility=JournalEntry.Visibility.PRIVATE,
        request_id=uuid4(),
    )

    calendar_data = journal_selectors.patient_journal_calendar_data(
        clinic_id=clinic.pk,
        actor=user,
        year=date.today().year,
        month=date.today().month,
    )

    assert calendar_data.year == date.today().year
    assert calendar_data.month == date.today().month
    assert len(calendar_data.days_header) == 7
    assert len(calendar_data.legend) == 5
    assert len(calendar_data.weeks) >= 4

    # Check that today's cell has dominant mood and accessible label
    today_found = False
    for week in calendar_data.weeks:
        for day in week:
            if day.is_today:
                today_found = True
                assert day.entry_count >= 1
                assert day.dominant_mood == JournalEntry.Mood.VERY_GOOD
                assert "Humor Muito bem" in day.accessible_label
    assert today_found


# ---------------------------------------------------------------------------
# 8.6.3 Sharing Traffic Light & Access Request Acceptance Tests
# ---------------------------------------------------------------------------


def test_sharing_traffic_light_yellow_request_grant_and_revoke_flow() -> None:
    """8.6.3: Test full flow of yellow request, approval, visibility and revocation."""
    clinic = ClinicFactory.create()
    administrator, user, profile = _linked_patient(clinic)
    therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    people_services.create_patient_care_relationship(
        clinic_id=clinic.pk,
        actor=administrator,
        therapist_id=therapist.pk,
        patient_profile_id=profile.pk,
        function="primary_therapist",
        valid_from=date.today(),
        valid_until=None,
        request_id=uuid4(),
    )

    # 1. Patient creates Yellow entry
    entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        mood=JournalEntry.Mood.NEUTRAL,
        emotions=["anxiety"],
        intensity=3,
        context="Registro sensível que exige confirmação prévia.",
        triggers="",
        reactions="",
        strategies="",
        visibility=JournalEntry.Visibility.CONFIRMATION_REQUIRED,
        request_id=uuid4(),
    )

    # 2. Therapist cannot see Yellow entry without active grant
    visible_before = journal_selectors.therapist_visible_journal_entries(
        clinic_id=clinic.pk, therapist_id=therapist.pk
    )
    assert visible_before == []

    # 3. Therapist requests access
    req = journal_services.request_journal_entry_access(
        clinic_id=clinic.pk,
        therapist=therapist,
        journal_entry_id=entry.pk,
        purpose="Acompanhamento e discussão terapêutica",
        expires_at=None,
        request_id=uuid4(),
    )
    assert req.status == JournalAccessRequest.Status.PENDING

    # 4-5. O paciente aprova pelo aplicativo (serviço usado pela API)
    req = journal_services.respond_journal_entry_access_request(
        clinic_id=clinic.pk,
        actor=user,
        access_request_id=req.pk,
        approved=True,
        expires_at=timezone.now() + timedelta(days=30),
        request_id=uuid4(),
    )
    assert req.status == JournalAccessRequest.Status.GRANTED
    assert req.expires_at is not None

    # 6. Now therapist query returns the granted Yellow entry
    visible_after_grant = journal_selectors.therapist_visible_journal_entries(
        clinic_id=clinic.pk, therapist_id=therapist.pk
    )
    assert [e.pk for e in visible_after_grant] == [entry.pk]

    # 7. O paciente revoga o compartilhamento pelo aplicativo
    journal_services.revoke_journal_entry_sharing(
        clinic_id=clinic.pk,
        actor=user,
        journal_entry_id=entry.pk,
        request_id=uuid4(),
    )
    entry.refresh_from_db()
    req.refresh_from_db()
    assert entry.visibility == JournalEntry.Visibility.PRIVATE
    assert req.status == JournalAccessRequest.Status.REVOKED

    # 8. Entry immediately vanishes from therapist view
    visible_after_revoke = journal_selectors.therapist_visible_journal_entries(
        clinic_id=clinic.pk, therapist_id=therapist.pk
    )
    assert visible_after_revoke == []


def test_therapist_cannot_request_access_to_private_red_entry() -> None:
    """8.6.3: Therapist cannot request access to a private (Red) entry."""
    clinic = ClinicFactory.create()
    administrator, user, profile = _linked_patient(clinic)
    therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    people_services.create_patient_care_relationship(
        clinic_id=clinic.pk,
        actor=administrator,
        therapist_id=therapist.pk,
        patient_profile_id=profile.pk,
        function="primary_therapist",
        valid_from=date.today(),
        valid_until=None,
        request_id=uuid4(),
    )

    private_entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        mood=JournalEntry.Mood.VERY_LOW,
        emotions=["anger"],
        intensity=5,
        context="Privado e estritamente confidencial.",
        triggers="",
        reactions="",
        strategies="",
        visibility=JournalEntry.Visibility.PRIVATE,
        request_id=uuid4(),
    )

    with pytest.raises(PermissionDenied):
        journal_services.request_journal_entry_access(
            clinic_id=clinic.pk,
            therapist=therapist,
            journal_entry_id=private_entry.pk,
            purpose="Quero ver",
            expires_at=None,
            request_id=uuid4(),
        )


def test_unlinked_therapist_cannot_request_access_to_yellow_entry() -> None:
    """8.6.3: Unlinked therapist is denied access request to any patient entry."""
    clinic = ClinicFactory.create()
    _administrator, user, profile = _linked_patient(clinic)
    unlinked_therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=unlinked_therapist, role=ClinicMembership.Role.THERAPIST
    )

    yellow_entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        mood=JournalEntry.Mood.NEUTRAL,
        emotions=["fear"],
        intensity=3,
        context="Entrada amarela de paciente sem vínculo com terapeuta.",
        triggers="",
        reactions="",
        strategies="",
        visibility=JournalEntry.Visibility.CONFIRMATION_REQUIRED,
        request_id=uuid4(),
    )

    with pytest.raises(PermissionDenied):
        journal_services.request_journal_entry_access(
            clinic_id=clinic.pk,
            therapist=unlinked_therapist,
            journal_entry_id=yellow_entry.pk,
            purpose="Tentativa sem vínculo",
            expires_at=None,
            request_id=uuid4(),
        )


def test_patient_can_reject_access_request() -> None:
    """8.6.3: Patient can reject an access request."""
    clinic = ClinicFactory.create()
    administrator, user, profile = _linked_patient(clinic)
    therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    people_services.create_patient_care_relationship(
        clinic_id=clinic.pk,
        actor=administrator,
        therapist_id=therapist.pk,
        patient_profile_id=profile.pk,
        function="primary_therapist",
        valid_from=date.today(),
        valid_until=None,
        request_id=uuid4(),
    )

    entry = journal_services.create_journal_entry(
        clinic_id=clinic.pk,
        actor=user,
        patient_profile_id=profile.pk,
        mood=JournalEntry.Mood.NEUTRAL,
        emotions=["calm"],
        intensity=3,
        context="Registro amarelo a ser recusado.",
        triggers="",
        reactions="",
        strategies="",
        visibility=JournalEntry.Visibility.CONFIRMATION_REQUIRED,
        request_id=uuid4(),
    )

    req = journal_services.request_journal_entry_access(
        clinic_id=clinic.pk,
        therapist=therapist,
        journal_entry_id=entry.pk,
        purpose="Discussão clínica",
        expires_at=None,
        request_id=uuid4(),
    )

    rejected = journal_services.respond_journal_entry_access_request(
        clinic_id=clinic.pk,
        actor=user,
        access_request_id=req.pk,
        approved=False,
        request_id=uuid4(),
    )

    assert rejected.status == JournalAccessRequest.Status.REJECTED
    assert (
        journal_selectors.therapist_visible_journal_entries(
            clinic_id=clinic.pk, therapist_id=therapist.pk
        )
        == []
    )
