"""Service layer for care plans, signing, and autonomy (8.14.5)."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.services import record_audit_event
from core.services import Service as CoreService

from .events import (
    care_plan_proposed,
    care_plan_response_received,
    care_plan_signed,
)
from .models import (
    CarePlan,
    CarePlanAction,
    CarePlanPatientResponse,
    CarePlanStatus,
    PatientResponseChoice,
)
from .policies import can_author_care_plan, can_prescribe_care_plan


class Service(CoreService[Any, Any]):
    """Care plan domain service base."""


@transaction.atomic
def propose_care_plan(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    professional_user: AbstractBaseUser,
    title: str,
    objective: str,
    clinical_rationale: str,
    contraindications: str = "",
    valid_from: date | None = None,
    valid_until: date | None = None,
    actions_data: list[dict[str, Any]] | None = None,
    request_id: UUID | None = None,
) -> CarePlan:
    """Propose a clinical care plan in DRAFT status awaiting clinician signature.

    A draft is never shown to the patient (see ``PATIENT_VISIBLE_PLAN_STATUSES``).
    """
    if not can_prescribe_care_plan(user=professional_user, clinic_id=clinic_id):
        raise ValidationError(
            "Apenas profissionais de saúde habilitados podem propor planos de cuidado."
        )

    clean_title = title.strip()
    clean_obj = objective.strip()
    clean_rationale = clinical_rationale.strip()

    if not clean_title or not clean_obj or not clean_rationale:
        raise ValidationError(
            "Título, objetivo e justificativa clínica são obrigatórios."
        )

    plan = CarePlan.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        prescribing_professional_id=professional_user.pk,
        title=clean_title,
        objective=clean_obj,
        clinical_rationale=clean_rationale,
        contraindications=contraindications.strip(),
        status=CarePlanStatus.DRAFT,
        version=1,
        valid_from=valid_from or timezone.localdate(),
        valid_until=valid_until,
    )

    _store_actions(clinic_id=clinic_id, plan=plan, actions_data=actions_data)
    _audit_plan(
        clinic_id=clinic_id,
        actor_id=professional_user.pk,
        request_id=request_id,
        action="routines.care_plan_proposed",
        plan=plan,
        justification="Professional proposed a care plan draft",
    )
    care_plan_proposed.send(sender=CarePlan, plan=plan)
    return plan


def _store_actions(
    *, clinic_id: UUID, plan: CarePlan, actions_data: list[dict[str, Any]] | None
) -> None:
    for idx, act in enumerate(actions_data or []):
        CarePlanAction.objects.for_clinic(clinic_id).create(
            clinic_id=clinic_id,
            care_plan=plan,
            action_description=act["description"].strip(),
            target_frequency=act.get("frequency", "daily"),
            guidance=act.get("guidance", "").strip(),
            is_mandatory=act.get("is_mandatory", False),
            order=idx,
        )


def _audit_plan(
    *,
    clinic_id: UUID,
    actor_id: UUID,
    request_id: UUID | None,
    action: str,
    plan: CarePlan,
    justification: str,
) -> None:
    """Audit a team change to a care plan (identifiers only, never its content)."""
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action=action,
        resource_type="care_plan",
        resource_id=str(plan.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=None,
        justification=justification,
    )


def _locked_plan(
    *, clinic_id: UUID, patient_profile_id: UUID, care_plan_id: UUID
) -> CarePlan:
    """Resolve one plan of this patient with a row lock (transitions are exclusive)."""
    plan = (
        CarePlan.objects.for_clinic(clinic_id)
        .select_for_update()
        .filter(pk=care_plan_id, patient_profile_id=patient_profile_id)
        .first()
    )
    if plan is None:
        raise ValidationError("Plano de cuidado não encontrado.")
    return plan


def _require_author(
    *, clinic_id: UUID, plan: CarePlan, professional_user: AbstractBaseUser
) -> None:
    if not can_author_care_plan(
        user=professional_user,
        clinic_id=clinic_id,
        prescribing_professional_id=plan.prescribing_professional_id,
    ):
        raise ValidationError(
            "Somente o profissional que propôs o plano pode editá-lo, enviá-lo "
            "para assinatura ou assiná-lo."
        )


@transaction.atomic
def update_care_plan_draft(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    title: str,
    objective: str,
    clinical_rationale: str,
    contraindications: str = "",
    valid_from: date | None = None,
    valid_until: date | None = None,
    actions_data: list[dict[str, Any]] | None = None,
    request_id: UUID | None = None,
) -> CarePlan:
    """Edit a plan that was never published; the actions are replaced as a set."""
    plan = _locked_plan(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
    )
    _require_author(clinic_id=clinic_id, plan=plan, professional_user=professional_user)
    if plan.status != CarePlanStatus.DRAFT:
        raise ValidationError("Só é possível editar um plano em rascunho.")
    clean_title = title.strip()
    clean_obj = objective.strip()
    clean_rationale = clinical_rationale.strip()
    if not clean_title or not clean_obj or not clean_rationale:
        raise ValidationError(
            "Título, objetivo e justificativa clínica são obrigatórios."
        )
    plan.title = clean_title
    plan.objective = clean_obj
    plan.clinical_rationale = clean_rationale
    plan.contraindications = contraindications.strip()
    plan.valid_from = valid_from or plan.valid_from
    plan.valid_until = valid_until
    plan.save()
    CarePlanAction.objects.for_clinic(clinic_id).filter(care_plan=plan).delete()
    _store_actions(clinic_id=clinic_id, plan=plan, actions_data=actions_data)
    _audit_plan(
        clinic_id=clinic_id,
        actor_id=professional_user.pk,
        request_id=request_id,
        action="routines.care_plan_updated",
        plan=plan,
        justification="Professional edited a care plan draft",
    )
    return plan


@transaction.atomic
def submit_care_plan_for_signature(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    request_id: UUID | None = None,
) -> CarePlan:
    """Lock a draft for its final review: DRAFT -> PENDING_SIGNATURE."""
    plan = _locked_plan(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
    )
    _require_author(clinic_id=clinic_id, plan=plan, professional_user=professional_user)
    if plan.status != CarePlanStatus.DRAFT:
        raise ValidationError("Só um rascunho pode ser enviado para assinatura.")
    has_actions = (
        CarePlanAction.objects.for_clinic(clinic_id).filter(care_plan=plan).exists()
    )
    if not has_actions:
        raise ValidationError(
            "Inclua ao menos uma ação antes de enviar para assinatura."
        )
    plan.status = CarePlanStatus.PENDING_SIGNATURE
    plan.save(update_fields=["status", "updated_at"])
    _audit_plan(
        clinic_id=clinic_id,
        actor_id=professional_user.pk,
        request_id=request_id,
        action="routines.care_plan_submitted",
        plan=plan,
        justification="Professional sent a care plan for signature",
    )
    return plan


@transaction.atomic
def reopen_care_plan_draft(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    request_id: UUID | None = None,
) -> CarePlan:
    """Send a plan awaiting signature back to draft so it can be edited."""
    plan = _locked_plan(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
    )
    _require_author(clinic_id=clinic_id, plan=plan, professional_user=professional_user)
    if plan.status != CarePlanStatus.PENDING_SIGNATURE:
        raise ValidationError("Só um plano aguardando assinatura volta a rascunho.")
    plan.status = CarePlanStatus.DRAFT
    plan.save(update_fields=["status", "updated_at"])
    _audit_plan(
        clinic_id=clinic_id,
        actor_id=professional_user.pk,
        request_id=request_id,
        action="routines.care_plan_reopened",
        plan=plan,
        justification="Professional returned a care plan to draft",
    )
    return plan


@transaction.atomic
def sign_care_plan(
    *,
    clinic_id: UUID,
    care_plan_id: UUID,
    signing_professional: AbstractBaseUser,
    request_id: UUID | None = None,
) -> CarePlan:
    """Digitally sign and activate care plan ensuring clinical governance."""
    if not can_prescribe_care_plan(user=signing_professional, clinic_id=clinic_id):
        raise ValidationError(
            "Apenas profissionais de saúde habilitados podem assinar planos de cuidado."
        )

    plan = (
        CarePlan.objects.for_clinic(clinic_id)
        .select_for_update()
        .filter(pk=care_plan_id)
        .first()
    )
    if not plan:
        raise ValidationError("Plano de cuidado não encontrado.")
    # Signing publishes the plan to the patient's app: a plan the patient refused
    # or that was closed must never be re-activated by signing it again.
    if plan.status not in {CarePlanStatus.DRAFT, CarePlanStatus.PENDING_SIGNATURE}:
        raise ValidationError("Este plano não está aguardando assinatura.")
    if plan.prescribing_professional_id != signing_professional.pk:
        raise ValidationError(
            "Somente o profissional que propôs o plano pode assiná-lo."
        )
    if (
        CarePlan.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=plan.patient_profile_id,
            status__in=[CarePlanStatus.ACTIVE, CarePlanStatus.PAUSED],
        )
        .exclude(pk=plan.pk)
        .exists()
    ):
        raise ValidationError(
            "O paciente já tem um plano de cuidado em vigor. Encerre-o antes de "
            "assinar outro."
        )

    now = timezone.now()
    secret = getattr(settings, "SECRET_KEY", "default-test-secret")
    digest = hashlib.sha256(
        f"{plan.id}:{signing_professional.pk}:{plan.version}:{now.isoformat()}:{secret}".encode()
    ).hexdigest()

    plan.status = CarePlanStatus.ACTIVE
    plan.signed_at = now
    plan.signature_digest = digest
    plan.save(update_fields=["status", "signed_at", "signature_digest", "updated_at"])

    record_audit_event(
        clinic_id=clinic_id,
        actor_id=signing_professional.pk,
        action="routines.care_plan_signed",
        resource_type="care_plan",
        resource_id=str(plan.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=None,
        justification=f"Professional signed care plan v{plan.version}",
    )

    care_plan_signed.send(sender=CarePlan, plan=plan)
    return plan


@transaction.atomic
def respond_to_care_plan(
    *,
    clinic_id: UUID,
    care_plan_id: UUID,
    decision: str,
    patient_notes: str = "",
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> CarePlanPatientResponse:
    """Record patient's autonomous decision regarding a proposed or active care plan."""
    plan = CarePlan.objects.for_clinic(clinic_id).filter(pk=care_plan_id).first()
    if not plan:
        raise ValidationError("Plano de cuidado não encontrado.")

    valid_choices = [c.value for c in PatientResponseChoice]
    if decision not in valid_choices:
        raise ValidationError(f"Decisão inválida: {decision}")

    response = CarePlanPatientResponse.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        care_plan=plan,
        plan_version_reviewed=plan.version,
        decision=decision,
        patient_notes=patient_notes.strip(),
        responded_at=timezone.now(),
    )

    if decision == PatientResponseChoice.PAUSED:
        plan.status = CarePlanStatus.PAUSED
        plan.save(update_fields=["status", "updated_at"])
    elif decision == PatientResponseChoice.REFUSED:
        plan.status = CarePlanStatus.REVOKED
        plan.save(update_fields=["status", "updated_at"])

    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="routines.care_plan_patient_response",
        resource_type="care_plan",
        resource_id=str(plan.id),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=None,
        justification=f"Patient responded with decision {decision}",
    )

    care_plan_response_received.send(sender=CarePlanPatientResponse, response=response)
    return response


def _transition(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    allowed_from: set[str],
    to_status: str,
    action: str,
    justification: str,
    error: str,
    request_id: UUID | None,
) -> CarePlan:
    """Move a published plan to another status on behalf of the team."""
    if not can_prescribe_care_plan(user=professional_user, clinic_id=clinic_id):
        raise ValidationError(
            "Apenas profissionais de saúde habilitados podem alterar planos de cuidado."
        )
    plan = _locked_plan(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
    )
    if plan.status not in allowed_from:
        raise ValidationError(error)
    plan.status = to_status
    plan.save(update_fields=["status", "updated_at"])
    _audit_plan(
        clinic_id=clinic_id,
        actor_id=professional_user.pk,
        request_id=request_id,
        action=action,
        plan=plan,
        justification=justification,
    )
    return plan


@transaction.atomic
def pause_care_plan(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    request_id: UUID | None = None,
) -> CarePlan:
    """Pause an active plan: the patient still sees it, marked as paused."""
    return _transition(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
        professional_user=professional_user,
        allowed_from={CarePlanStatus.ACTIVE},
        to_status=CarePlanStatus.PAUSED,
        action="routines.care_plan_paused",
        justification="Team paused a care plan",
        error="Só um plano ativo pode ser pausado.",
        request_id=request_id,
    )


@transaction.atomic
def resume_care_plan(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    request_id: UUID | None = None,
) -> CarePlan:
    """Resume a paused plan (the team decision; the patient is told in the app)."""
    return _transition(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
        professional_user=professional_user,
        allowed_from={CarePlanStatus.PAUSED},
        to_status=CarePlanStatus.ACTIVE,
        action="routines.care_plan_resumed",
        justification="Team resumed a paused care plan",
        error="Só um plano pausado pode ser retomado.",
        request_id=request_id,
    )


@transaction.atomic
def close_care_plan(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    care_plan_id: UUID,
    professional_user: AbstractBaseUser,
    outcome: str = CarePlanStatus.COMPLETED,
    request_id: UUID | None = None,
) -> CarePlan:
    """End a published plan as completed or revoked; a closed plan accepts no reply.

    Drafts and plans awaiting signature are never closed here: ``revoked`` is visible
    to the patient, so using it on an unpublished draft would expose it.
    """
    if outcome not in {CarePlanStatus.COMPLETED, CarePlanStatus.REVOKED}:
        raise ValidationError("Resultado de encerramento inválido.")
    return _transition(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        care_plan_id=care_plan_id,
        professional_user=professional_user,
        allowed_from={CarePlanStatus.ACTIVE, CarePlanStatus.PAUSED},
        to_status=outcome,
        action="routines.care_plan_closed",
        justification=f"Team closed a care plan as {outcome}",
        error="Só um plano ativo ou pausado pode ser encerrado.",
        request_id=request_id,
    )


__all__ = [
    "Service",
    "close_care_plan",
    "pause_care_plan",
    "propose_care_plan",
    "reopen_care_plan_draft",
    "respond_to_care_plan",
    "resume_care_plan",
    "sign_care_plan",
    "submit_care_plan_for_signature",
    "update_care_plan_draft",
]
