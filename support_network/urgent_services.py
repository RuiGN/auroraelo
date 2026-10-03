"""Services for urgent support plans and explicit emergency actions (8.16.3)."""

from __future__ import annotations

from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from audit.services import record_audit_event
from support_network.contracts import UrgentActionPreview
from support_network.events import (
    urgent_action_confirmed,
    urgent_action_previewed,
    urgent_plan_updated,
)
from support_network.urgent_plan_models import (
    MANDATORY_URGENT_DISCLAIMER,
    UrgentActionLog,
    UrgentSupportContact,
    UrgentSupportPlan,
)

DEFAULT_CONTACT_MESSAGE = (
    "Olá, estou em um momento difícil e gostaria de conversar ou de sua "
    "presença, quando puder."
)


class UrgentContactLimitError(ValueError):
    """The plan already has the maximum number of active contacts."""


@transaction.atomic
def create_or_update_urgent_plan(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    personal_instructions: str = "",
    calming_strategies: list[str] | None = None,
    preferred_language: str = "pt-BR",
    region: str = "BR",
    review_period_days: int = 90,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
    network_origin: str | None = None,
) -> UrgentSupportPlan:
    """Create or update personal plan for urgent moments.

    Saving the plan never contacts anyone: a call or message only happens when the
    patient taps it on the device. The audit trail never carries the plan text.
    """
    plan, _ = UrgentSupportPlan.objects.for_clinic(clinic_id).update_or_create(
        clinic_id=clinic_id,
        patient_id=patient_profile_id,
        defaults={
            "personal_instructions": personal_instructions.strip(),
            "calming_strategies": calming_strategies or [],
            "preferred_language": preferred_language,
            "region": region,
            "review_period_days": review_period_days,
            "last_reviewed_at": timezone.now(),
            "disclaimer_acknowledged": True,
        },
    )

    urgent_plan_updated.send(sender=UrgentSupportPlan, plan=plan)
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="support_network.urgent_plan_updated",
        resource_type="urgent_plan",
        resource_id=str(plan.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=network_origin,
    )
    return plan


@transaction.atomic
def register_urgent_contact(
    *,
    clinic_id: UUID,
    plan_id: UUID,
    name: str,
    relationship: str,
    phone_number: str,
    priority_order: int | None = 1,
    message_template: str = "",
    max_active_contacts: int | None = None,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
    network_origin: str | None = None,
) -> UrgentSupportContact:
    """Register a contact in the urgent support plan.

    With ``max_active_contacts`` the plan row is locked and the limit is checked in
    the same transaction (``UrgentContactLimitError``), so two concurrent requests
    cannot exceed it. ``priority_order=None`` appends after the active contacts.
    The audit trail never carries the contact's name or phone number.
    """
    plan_query = UrgentSupportPlan.objects.for_clinic(clinic_id).filter(id=plan_id)
    if max_active_contacts is not None:
        plan_query = plan_query.select_for_update()
    plan = plan_query.first()
    if not plan:
        raise ValueError("Plano de apoio urgente não encontrado.")

    active = UrgentSupportContact.objects.for_clinic(clinic_id).filter(
        plan=plan, is_active=True
    )
    if max_active_contacts is not None and active.count() >= max_active_contacts:
        raise UrgentContactLimitError("Limite de contatos do plano atingido.")
    if priority_order is None:
        last = active.aggregate(last=Max("priority_order"))["last"]
        priority_order = (last or 0) + 1

    contact = UrgentSupportContact.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        plan=plan,
        priority_order=priority_order,
        name=name.strip(),
        relationship=relationship.strip(),
        phone_number=phone_number.strip(),
        message_template=message_template.strip() or DEFAULT_CONTACT_MESSAGE,
        is_active=True,
    )

    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="support_network.urgent_contact_added",
        resource_type="urgent_contact",
        resource_id=str(contact.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=network_origin,
    )
    return contact


def _own_active_contact(
    *, clinic_id: UUID, patient_profile_id: UUID, contact_id: UUID
) -> UrgentSupportContact:
    """The patient's own active contact, locked for update; otherwise ``ValueError``."""
    contact = (
        UrgentSupportContact.objects.for_clinic(clinic_id)
        .select_for_update()
        .filter(id=contact_id, plan__patient_id=patient_profile_id, is_active=True)
        .first()
    )
    if contact is None:
        raise ValueError("Contato de apoio urgente não encontrado.")
    return contact


@transaction.atomic
def update_urgent_contact(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    contact_id: UUID,
    name: str,
    relationship: str,
    phone_number: str,
    message_template: str = "",
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
    network_origin: str | None = None,
) -> UrgentSupportContact:
    """Change one of the patient's own active contacts; order is kept."""
    contact = _own_active_contact(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        contact_id=contact_id,
    )
    contact.name = name.strip()
    contact.relationship = relationship.strip()
    contact.phone_number = phone_number.strip()
    contact.message_template = message_template.strip() or DEFAULT_CONTACT_MESSAGE
    contact.save(
        update_fields=[
            "name",
            "relationship",
            "phone_number",
            "message_template",
            "updated_at",
        ]
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="support_network.urgent_contact_updated",
        resource_type="urgent_contact",
        resource_id=str(contact.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=network_origin,
    )
    return contact


@transaction.atomic
def deactivate_urgent_contact(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    contact_id: UUID,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
    network_origin: str | None = None,
) -> UrgentSupportContact:
    """Take one of the patient's own contacts out of the plan (kept as inactive)."""
    contact = _own_active_contact(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        contact_id=contact_id,
    )
    contact.is_active = False
    contact.save(update_fields=["is_active", "updated_at"])
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="support_network.urgent_contact_removed",
        resource_type="urgent_contact",
        resource_id=str(contact.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=network_origin,
    )
    return contact


def prepare_urgent_action_preview(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    contact_id: UUID,
    actor_id: UUID | None = None,
) -> UrgentActionPreview:
    """Generate explicit preview for user confirmation before any contact action.

    Never sends silent dispatches or automated crisis triggers.
    """
    contact = (
        UrgentSupportContact.objects.for_clinic(clinic_id)
        .filter(id=contact_id, plan__patient_id=patient_profile_id, is_active=True)
        .first()
    )
    if not contact:
        raise ValueError("Contato de apoio urgente não encontrado ou inativo.")

    preview = UrgentActionPreview(
        contact_id=contact.id,
        contact_name=contact.name,
        contact_phone=contact.phone_number,
        message_content=contact.message_template,
        requires_explicit_confirmation=True,
        disclaimer=MANDATORY_URGENT_DISCLAIMER,
    )

    UrgentActionLog.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_id=patient_profile_id,
        contact_id=contact.id,
        action_type="PREVIEW_GENERATED",
        confirmed_explicitly=False,
        disclaimer_shown=True,
    )

    urgent_action_previewed.send(sender=UrgentSupportContact, preview=preview)
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="support_network.urgent_action_previewed",
        resource_type="urgent_contact",
        resource_id=str(contact.id),
        outcome="success",
        request_id=uuid4(),
        network_origin=None,
    )
    return preview


@transaction.atomic
def confirm_urgent_contact_action(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    contact_id: UUID,
    confirmed_by_user: bool,
    actor_id: UUID | None = None,
) -> UrgentActionLog:
    """Record explicit user-confirmed intention to contact support contact."""
    if not confirmed_by_user:
        raise ValueError(
            "Ação cancelada: envio exige confirmação explícita do usuário."
        )

    contact = (
        UrgentSupportContact.objects.for_clinic(clinic_id)
        .filter(id=contact_id, plan__patient_id=patient_profile_id, is_active=True)
        .first()
    )
    if not contact:
        raise ValueError("Contato de apoio urgente não encontrado.")

    log = UrgentActionLog.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_id=patient_profile_id,
        contact_id=contact.id,
        action_type="CONFIRMED_BY_USER",
        confirmed_explicitly=True,
        disclaimer_shown=True,
    )

    urgent_action_confirmed.send(
        sender=UrgentActionLog,
        log=log,
        contact_phone=contact.phone_number,
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="support_network.urgent_action_confirmed",
        resource_type="urgent_contact",
        resource_id=str(contact.id),
        outcome="success",
        request_id=uuid4(),
        network_origin=None,
    )
    return log


__all__ = [
    "DEFAULT_CONTACT_MESSAGE",
    "UrgentContactLimitError",
    "confirm_urgent_contact_action",
    "create_or_update_urgent_plan",
    "deactivate_urgent_contact",
    "prepare_urgent_action_preview",
    "register_urgent_contact",
    "update_urgent_contact",
]
