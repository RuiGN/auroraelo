"""Acceptance coverage for the second-round authorization and audit hardening."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils import timezone

from accounts.forms import translated_membership_role_label
from accounts.services import accept_invitation, issue_invitation
from audit.models import AuditEvent
from clinics.admin import ClinicAdmin, ClinicMembershipAdmin
from clinics.models import Clinic, ClinicMembership
from clinics.services import (
    create_clinic_membership,
    ensure_membership_activatable,
)
from master_panel.services import _on_subscription_deleted
from master_panel.tenant_services import ensure_tenant_subscription
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory


@pytest.mark.django_db
def test_activation_rule_blocks_only_an_expired_window() -> None:
    """A future window is the model's scheduled state; an expired one must renew."""
    today = timezone.localdate()

    ensure_membership_activatable(
        valid_from=today + timedelta(days=10), valid_until=None
    )
    ensure_membership_activatable(valid_from=today, valid_until=today)

    with pytest.raises(ValidationError):
        ensure_membership_activatable(
            valid_from=today - timedelta(days=30),
            valid_until=today - timedelta(days=1),
        )


@pytest.mark.django_db
def test_creation_keeps_scheduling_and_rejects_an_expired_active_link() -> None:
    """Creating an active link never accepts a window that already expired."""
    clinic = ClinicFactory.create()
    scheduled_user = UserFactory.create()
    expired_user = UserFactory.create()
    today = timezone.localdate()

    scheduled = create_clinic_membership(
        clinic_id=clinic.pk,
        user_id=scheduled_user.pk,
        role=ClinicMembership.Role.THERAPIST,
        valid_from=today + timedelta(days=7),
    )
    assert scheduled.is_active is True
    assert scheduled.professional_status(on_date=today) == "scheduled"

    future_inactive = create_clinic_membership(
        clinic_id=clinic.pk,
        user_id=UserFactory.create().pk,
        role=ClinicMembership.Role.THERAPIST,
        valid_from=today + timedelta(days=30),
        is_active=False,
    )
    assert future_inactive.is_active is False

    with pytest.raises(ValidationError):
        create_clinic_membership(
            clinic_id=clinic.pk,
            user_id=expired_user.pk,
            role=ClinicMembership.Role.THERAPIST,
            valid_from=today - timedelta(days=30),
            valid_until=today - timedelta(days=1),
        )
    assert not ClinicMembership.infrastructure_objects.filter(
        clinic=clinic, user=expired_user
    ).exists()


@pytest.mark.django_db
def test_clinic_membership_admin_is_inspection_only() -> None:
    """Admin must not create, edit or delete memberships outside the services."""
    request = RequestFactory().get("/admin/clinics/clinicmembership/")
    request.user = UserFactory.create(is_staff=True, is_superuser=True)
    model_admin = ClinicMembershipAdmin(ClinicMembership, admin.site)

    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
    assert model_admin.has_view_permission(request) is True
    readonly = model_admin.get_readonly_fields(request, None)
    for field in ("role", "is_active", "valid_from", "valid_until", "authorized_by"):
        assert field in readonly


@pytest.mark.django_db
def test_clinic_admin_keeps_activation_read_only() -> None:
    """Clinic activation is an audited operator action, never a free-form edit."""
    request = RequestFactory().get("/admin/clinics/clinic/")
    request.user = UserFactory.create(is_staff=True, is_superuser=True)
    clinic_admin = ClinicAdmin(Clinic, admin.site)

    clinic = ClinicFactory.create()
    assert "is_active" in clinic_admin.get_readonly_fields(request, clinic)
    assert "is_active" in clinic_admin.get_readonly_fields(request, None)


@pytest.mark.django_db
def test_provider_driven_subscription_transition_is_audited() -> None:
    """A payment-provider status change leaves the same audit trail."""
    clinic = ClinicFactory.create()
    subscription = ensure_tenant_subscription(clinic_id=clinic.pk)
    subscription.stripe_subscription_id = "sub_sintetico_nao_real"
    subscription.save(update_fields=["stripe_subscription_id", "updated_at"])

    _on_subscription_deleted({"id": "sub_sintetico_nao_real"})

    events = AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk, resource_type="tenant_subscription"
    )
    assert events.count() == 1
    event = events.first()
    assert event is not None
    assert event.actor_id is None
    assert event.resource_id == str(subscription.pk)


@pytest.mark.django_db
def test_invitation_acceptance_records_the_authorization_change() -> None:
    """Accepting an invitation records who granted the membership role."""
    clinic = ClinicFactory.create()
    issuer = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=issuer,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )

    issued = issue_invitation(
        clinic_id=clinic.pk,
        issuer=issuer,
        recipient_email="convidada.auditoria@example.test",
        initial_role=ClinicMembership.Role.THERAPIST,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    invited_user = accept_invitation(
        raw_token=issued.raw_token,
        password="senha-sintetica-longa-e-nao-reutilizavel",
        first_name="Pessoa",
        last_name="Convidada",
    )

    membership = ClinicMembership.infrastructure_objects.get(
        clinic=clinic, user=invited_user
    )
    assert membership.authorized_by_id == issuer.pk
    assert AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk,
        actor_id=issuer.pk,
        resource_type="clinic_membership",
        resource_id=str(membership.pk),
    ).exists()


@pytest.mark.django_db
def test_unknown_role_label_falls_back_to_a_translated_message() -> None:
    """The UI never renders an untranslated model display name."""
    assert translated_membership_role_label(ClinicMembership.Role.CLINIC_ADMIN) == (
        "Administrador da clínica"
    )
    fallback = translated_membership_role_label("papel_inexistente_sintetico")
    assert fallback != "papel_inexistente_sintetico"
    assert fallback == "Papel não reconhecido"


@pytest.mark.django_db
def test_role_change_and_audit_commit_together() -> None:
    """The role change records its author and its audit row in one commit."""
    from clinics.services import update_membership_role

    clinic = ClinicFactory.create()
    actor = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=actor, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    target = UserFactory.create()
    membership = ClinicMembershipFactory.create(
        clinic=clinic, user=target, role=ClinicMembership.Role.THERAPIST
    )

    update_membership_role(
        actor=actor,
        clinic=clinic,
        membership_id=membership.pk,
        role=ClinicMembership.Role.ADMINISTRATIVE_STAFF,
        request_id=uuid4(),
    )
    membership.refresh_from_db()
    assert membership.role == ClinicMembership.Role.ADMINISTRATIVE_STAFF
    assert membership.authorized_by_id == actor.pk
    assert AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk,
        actor_id=actor.pk,
        resource_type="clinic_membership",
        resource_id=str(membership.pk),
    ).exists()
    assert date.today() >= membership.valid_from
