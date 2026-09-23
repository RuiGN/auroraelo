"""Acceptance coverage for global and clinic-scoped user administration."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from django.conf import settings
from django.contrib import admin
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext

from accounts.admin import AuroraUserAdmin, ClinicMembershipInline
from accounts.events import account_audit_required
from accounts.forms import translated_membership_role_choices
from accounts.models import ClinicInvitation, User
from accounts.services import issue_invitation
from clinics.events import membership_authorization_changed
from clinics.models import Clinic, ClinicMembership
from clinics.services import (
    reactivate_professional_membership,
    set_membership_active,
    update_membership_role,
)
from master_panel.tenant_services import set_tenant_blocked
from master_panel.user_services import (
    link_or_update_membership,
    update_membership_as_operator,
)
from people.models import ProfessionalProfile
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db


def _master(client: Client) -> User:
    user = UserFactory.create(is_staff=True, is_superuser=True)
    client.force_login(user)
    return user


def test_master_user_list_is_available_to_global_staff(client: Client) -> None:
    """Master can inspect memberships without an active clinic session."""
    _master(client)
    clinic = ClinicFactory.create(name="Clínica de usuários")
    member = UserFactory.create(email="membro@example.test")
    ClinicMembershipFactory.create(clinic=clinic, user=member)

    response = client.get(reverse("administration:user_list"))

    assert response.status_code == 200
    assert member.email in response.content.decode()
    assert clinic.name in response.content.decode()


def test_master_links_existing_identity_and_creates_psychiatrist_profile(
    client: Client,
) -> None:
    """Existing identities are linked without creating or revealing a password."""
    master = _master(client)
    clinic = ClinicFactory.create(name="Clínica de psiquiatria")
    user = UserFactory.create(email="psiquiatra@example.test")

    response = client.post(
        reverse("administration:user_invite"),
        {
            "recipient_email": user.email,
            "clinic": str(clinic.pk),
            "initial_role": ClinicMembership.Role.THERAPIST,
            "initial_category": ProfessionalProfile.Category.PSYCHIATRIST,
            "unit_name": "Unidade Centro",
            "valid_from": date.today().isoformat(),
            "valid_until": "",
            "expires_in_hours": "24",
        },
    )

    assert response.status_code == 302
    membership = ClinicMembership.infrastructure_objects.get(clinic=clinic, user=user)
    assert membership.authorized_by_id == master.pk
    assert membership.unit_name == "Unidade Centro"
    profile = ProfessionalProfile.infrastructure_objects.get(clinic=clinic, user=user)
    assert profile.category == ProfessionalProfile.Category.PSYCHIATRIST
    assert not ClinicInvitation.infrastructure_objects.filter(
        recipient_email=user.email, used_at__isnull=True
    ).exists()


def test_master_invitation_persists_scope_and_sends_no_password(client: Client) -> None:
    """New users receive a one-use invitation carrying role metadata only."""
    _master(client)
    clinic = ClinicFactory.create(name="Clínica de convites")

    response = client.post(
        reverse("administration:user_invite"),
        {
            "recipient_email": "novo.profissional@example.test",
            "clinic": str(clinic.pk),
            "initial_role": ClinicMembership.Role.THERAPIST,
            "initial_category": ProfessionalProfile.Category.PSYCHOLOGIST,
            "unit_name": "Unidade Norte",
            "valid_from": date.today().isoformat(),
            "valid_until": (date.today() + timedelta(days=30)).isoformat(),
            "expires_in_hours": "24",
        },
    )

    assert response.status_code == 302
    invitation = ClinicInvitation.infrastructure_objects.get(
        recipient_email="novo.profissional@example.test"
    )
    assert invitation.initial_category == ProfessionalProfile.Category.PSYCHOLOGIST
    assert invitation.unit_name == "Unidade Norte"
    assert invitation.valid_until == date.today() + timedelta(days=30)
    assert len(mail.outbox) == 1
    assert "password" not in mail.outbox[0].body.casefold()


def test_clinic_team_never_lists_other_clinic_members(client: Client) -> None:
    """The clinic UI is scoped by both session selection and membership policy."""
    clinic = ClinicFactory.create(name="Clínica A")
    other = ClinicFactory.create(name="Clínica B")
    admin = UserFactory.create()
    visible = UserFactory.create(email="visivel@example.test")
    hidden = UserFactory.create(email="oculto@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=admin,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    ClinicMembershipFactory.create(clinic=clinic, user=visible)
    hidden_membership = ClinicMembershipFactory.create(clinic=other, user=hidden)
    client.force_login(admin)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()

    response = client.get(reverse("team_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert visible.email in content
    assert hidden.email not in content
    with pytest.raises(PermissionDenied):
        set_membership_active(
            clinic_id=clinic.pk,
            actor=admin,
            membership_id=hidden_membership.pk,
            is_active=False,
            request_id=uuid4(),
        )


def test_patient_and_non_staff_cannot_open_master_user_management(
    client: Client,
) -> None:
    """Global user management is not inherited by clinic identities."""
    user = UserFactory.create(is_staff=False, is_superuser=False)
    client.force_login(user)

    response = client.get(reverse("administration:user_list"))

    assert response.status_code == 302
    assert "/master/login/" in response.headers["Location"]


def test_deactivated_staff_loses_global_and_tenant_authority() -> None:
    """A disabled global operator cannot issue invitations or link memberships."""
    operator = UserFactory.create(is_staff=True, is_superuser=True, is_active=False)
    clinic = ClinicFactory.create(name="Clínica de operador inativo")
    target = UserFactory.create(email="alvo.inativo@example.test")

    with pytest.raises(PermissionDenied):
        issue_invitation(
            clinic_id=clinic.pk,
            issuer=operator,
            recipient_email="convidado.inativo@example.test",
            initial_role=ClinicMembership.Role.THERAPIST,
            expires_at=timezone.now() + timedelta(hours=1),
        )
    with pytest.raises(PermissionDenied):
        link_or_update_membership(
            actor=operator,
            user=target,
            clinic_id=clinic.pk,
            role=ClinicMembership.Role.THERAPIST,
        )
    assert not ClinicMembership.infrastructure_objects.filter(
        clinic=clinic, user=target
    ).exists()
    assert not ClinicInvitation.infrastructure_objects.filter(clinic=clinic).exists()


def test_admin_membership_inline_is_inspection_only() -> None:
    """Django Admin cannot mutate membership outside the audited service."""
    inline = ClinicMembershipInline(ClinicMembership, admin.site)

    assert not inline.has_add_permission(None)  # type: ignore[arg-type]
    assert not inline.has_change_permission(None)  # type: ignore[arg-type]
    assert not inline.has_delete_permission(None)  # type: ignore[arg-type]
    assert inline.readonly_fields == inline.fields


def test_reactivating_an_expired_membership_is_rejected() -> None:
    """Reactivation must not advertise an active link outside its validity."""
    clinic = ClinicFactory.create(name="Clínica de reativação")
    admin_user = UserFactory.create(email="admin.reativacao@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=admin_user,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    expired = ClinicMembershipFactory.create(
        clinic=clinic,
        user=UserFactory.create(email="expirado@example.test"),
        is_active=False,
        valid_from=date.today() - timedelta(days=30),
        valid_until=date.today() - timedelta(days=1),
    )

    with pytest.raises(ValidationError):
        set_membership_active(
            clinic_id=clinic.pk,
            actor=admin_user,
            membership_id=expired.pk,
            is_active=True,
            request_id=uuid4(),
        )

    expired.refresh_from_db()
    assert expired.is_active is False


def _clinic_admin_session(client: Client, *, clinic: Clinic) -> User:
    """Sign in a clinic administrator whose active session clinic is explicit."""
    admin_user = UserFactory.create(email="admin.equipe@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=admin_user,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    client.force_login(admin_user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return admin_user


def test_clinic_team_revokes_and_resends_only_its_own_invitations(
    client: Client,
) -> None:
    """Invitation management stays inside the clinic selected in the session."""
    clinic = ClinicFactory.create(name="Clínica de convites")
    other_clinic = ClinicFactory.create(name="Clínica alheia")
    admin_user = _clinic_admin_session(client, clinic=clinic)
    issued = issue_invitation(
        clinic_id=clinic.pk,
        issuer=admin_user,
        recipient_email="pendente@example.test",
        initial_role=ClinicMembership.Role.THERAPIST,
        expires_at=timezone.now() + timedelta(hours=4),
    )
    foreign = issue_invitation(
        clinic_id=other_clinic.pk,
        issuer=UserFactory.create(is_staff=True, email="operador.global@example.test"),
        recipient_email="alheio@example.test",
        initial_role=ClinicMembership.Role.THERAPIST,
        expires_at=timezone.now() + timedelta(hours=4),
    )
    mail.outbox.clear()

    listing = client.get(reverse("team_list"))

    assert listing.status_code == 200
    content = listing.content.decode()
    assert "pendente@example.test" in content
    assert "alheio@example.test" not in content

    revoked = client.post(
        reverse(
            "team_revoke_invitation", kwargs={"invitation_id": issued.invitation.pk}
        )
    )

    assert revoked.status_code == 302
    issued.invitation.refresh_from_db()
    assert issued.invitation.revoked_at is not None

    crossing = client.post(
        reverse(
            "team_revoke_invitation", kwargs={"invitation_id": foreign.invitation.pk}
        )
    )

    assert crossing.status_code == 302
    foreign.invitation.refresh_from_db()
    assert foreign.invitation.revoked_at is None

    resent = issue_invitation(
        clinic_id=clinic.pk,
        issuer=admin_user,
        recipient_email="reenvio@example.test",
        initial_role=ClinicMembership.Role.THERAPIST,
        expires_at=timezone.now() + timedelta(hours=4),
    )
    responses = client.post(
        reverse(
            "team_resend_invitation",
            kwargs={"invitation_id": resent.invitation.pk},
        )
    )

    assert responses.status_code == 302
    resent.invitation.refresh_from_db()
    assert resent.invitation.revoked_at is not None
    replacement = ClinicInvitation.infrastructure_objects.get(
        clinic=clinic,
        recipient_email="reenvio@example.test",
        used_at__isnull=True,
        revoked_at__isnull=True,
    )
    assert replacement.pk != resent.invitation.pk
    assert len(mail.outbox) == 1
    assert "reenvio@example.test" in mail.outbox[0].to


def test_clinic_member_without_admin_role_cannot_open_team_management(
    client: Client,
) -> None:
    """Membership administration is denied for non-administrative roles."""
    clinic = ClinicFactory.create(name="Clínica sem administrador")
    member = UserFactory.create(email="terapeuta.equipe@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=member,
        role=ClinicMembership.Role.THERAPIST,
    )
    client.force_login(member)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()

    response = client.get(reverse("team_list"))

    assert response.status_code == 403


def _clinic_admin(clinic: Clinic) -> User:
    """Create an actor authorized to manage professionals in one clinic."""
    actor = UserFactory.create(email=f"admin.{uuid4().hex[:8]}@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=actor,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    return actor


def test_expired_professional_membership_cannot_be_reactivated() -> None:
    """The professional reactivation path shares the validity rule of the team UI."""
    clinic = ClinicFactory.create(name="Clínica de reativação")
    actor = _clinic_admin(clinic)
    target = UserFactory.create(email="expirado@example.test")
    membership = ClinicMembershipFactory.create(
        clinic=clinic,
        user=target,
        role=ClinicMembership.Role.THERAPIST,
        is_active=False,
        valid_from=date.today() - timedelta(days=90),
        valid_until=date.today() - timedelta(days=1),
    )

    with pytest.raises(ValidationError):
        reactivate_professional_membership(
            clinic_id=clinic.pk,
            actor=actor,
            membership_id=membership.pk,
            request_id=uuid4(),
        )

    membership.refresh_from_db()
    assert membership.is_active is False


def test_master_operator_cannot_activate_membership_outside_validity() -> None:
    """Global administration cannot bypass the validity window either."""
    operator = UserFactory.create(
        is_staff=True,
        is_superuser=True,
        email="operador.validade@example.test",
    )
    clinic = ClinicFactory.create(name="Clínica de validade")
    target = UserFactory.create(email="fora.validade@example.test")
    membership = ClinicMembershipFactory.create(
        clinic=clinic,
        user=target,
        is_active=False,
        valid_from=date.today() - timedelta(days=30),
        valid_until=date.today() - timedelta(days=2),
    )

    with pytest.raises(ValidationError):
        update_membership_as_operator(
            actor=operator,
            membership_id=membership.pk,
            role=membership.role,
            category="",
            unit_name="",
            valid_from=membership.valid_from,
            valid_until=membership.valid_until,
            is_active=True,
        )

    membership.refresh_from_db()
    assert membership.is_active is False


def test_global_privileges_are_read_only_in_the_django_admin() -> None:
    """Administrative saves cannot escalate privileges outside the audited path."""
    model_admin = AuroraUserAdmin(User, admin.site)

    for field in (
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
    ):
        assert field in model_admin.readonly_fields


def test_blocking_a_clinic_is_audited_and_requires_active_staff() -> None:
    """Tenant block/unblock goes through one audited service."""
    captured: list[dict[str, object]] = []

    def _capture(sender: object, **kwargs: object) -> None:
        captured.append(kwargs)

    account_audit_required.connect(_capture, weak=False)
    try:
        clinic = ClinicFactory.create(name="Clínica de bloqueio")
        operator = UserFactory.create(
            is_staff=True,
            is_superuser=True,
            email="operador.bloqueio@example.test",
        )
        set_tenant_blocked(
            actor=operator,
            clinic_id=clinic.pk,
            blocked=True,
            reason="Ensaio sintético",
        )
        assert captured, "auditoria de bloqueio não emitida"
        last = captured[-1]
        assert last["clinic_id"] == clinic.pk
        assert last["actor_id"] == operator.pk
        assert last["resource_type"] == "tenant_subscription"

        with pytest.raises(PermissionDenied):
            set_tenant_blocked(
                actor=UserFactory.create(email="nao.staff@example.test"),
                clinic_id=clinic.pk,
                blocked=False,
            )
    finally:
        account_audit_required.disconnect(_capture)


def test_role_update_service_records_author_and_audit() -> None:
    """Public role changes keep authorship and emit the authorization event."""
    clinic = ClinicFactory.create(name="Clínica de papel")
    actor = _clinic_admin(clinic)
    target = UserFactory.create(email="papel@example.test")
    membership = ClinicMembershipFactory.create(
        clinic=clinic,
        user=target,
        role=ClinicMembership.Role.PATIENT,
    )
    captured: list[dict[str, object]] = []

    def _capture(sender: object, **kwargs: object) -> None:
        captured.append(kwargs)

    membership_authorization_changed.connect(_capture, weak=False)
    try:
        updated = update_membership_role(
            actor=actor,
            clinic=clinic,
            membership_id=membership.pk,
            role=ClinicMembership.Role.THERAPIST,
        )
    finally:
        membership_authorization_changed.disconnect(_capture)

    assert updated.role == ClinicMembership.Role.THERAPIST
    assert updated.authorized_by_id == actor.pk
    assert captured and captured[-1]["actor_id"] == actor.pk

    with pytest.raises(ValidationError):
        update_membership_role(
            actor=actor,
            clinic=clinic,
            membership_id=membership.pk,
            role="invented_role",
        )


def test_role_labels_stay_translatable_in_both_administrations() -> None:
    """Role labels keep stable codes while remaining translatable in the UI."""
    with translation.override("pt-br"):
        portuguese = dict(translated_membership_role_choices())
        portuguese_label = str(portuguese["clinic_admin"])
    with translation.override("en"):
        english_label = gettext("Administrador da clínica")

    assert portuguese_label == "Administrador da clínica"
    assert english_label == "Clinic administrator"

    base = Path(settings.BASE_DIR)
    for template in (
        "master_panel/templates/master_panel/users.html",
        "templates/accounts/team.html",
    ):
        body = (base / template).read_text(encoding="utf-8")
        assert "row.role_label" in body
        assert "get_role_display" not in body
