"""Grants explícitos nunca substituem identidade, vínculo ou consentimento."""

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from clinics.policies import has_active_clinic_role
from clinics.services import authorized_active_clinic
from consents.policies import ConsentPurpose
from consents.services import require_purpose_access
from core.policies import AuthorizationPolicy as AuthorizationPolicy
from people.selectors import patient_visible_to

from .models import OperationGrant

CAPABILITIES = frozenset(
    {
        "pharmacy.read",
        "pharmacy.write",
        "encounter.manage",
        "record.read",
        "record.write",
        "session.manage",
    }
)


def require_capability(*, clinic_id, actor, capability):
    clinic = authorized_active_clinic(
        clinic_id=clinic_id, actor=actor, action="clinic.read"
    )
    if (
        capability not in CAPABILITIES
        or not OperationGrant.objects.for_clinic(clinic_id)
        .filter(user_id=actor.pk, capability=capability, enabled=True)
        .exists()
    ):
        raise PermissionDenied("Grant explícito necessário.")
    if capability in {
        "record.read",
        "record.write",
        "encounter.manage",
        "session.manage",
    } and not has_active_clinic_role(
        clinic_id=clinic_id,
        user_id=actor.pk,
        role="therapist",
        on_date=timezone.localdate(),
    ):
        raise PermissionDenied("Profissional ativo necessário.")
    return clinic


def require_patient_access(*, clinic_id, actor, patient_id, capability, consent=False):
    clinic = require_capability(clinic_id=clinic_id, actor=actor, capability=capability)
    if (
        patient_visible_to(
            actor=actor,
            clinic=clinic,
            patient_id=patient_id,
            action="patient.clinical.read",
        )
        is None
    ):
        raise PermissionDenied("Vínculo clínico ativo necessário.")
    if consent:
        require_purpose_access(
            clinic_id=clinic_id,
            subject_id=patient_id,
            purpose=ConsentPurpose.CLINICAL_FOLLOW_UP,
        )


def require_encounter_access(*, clinic_id, actor, encounter, capability, consent=False):
    if encounter.clinic_id != clinic_id or encounter.professional_id != actor.pk:
        raise PermissionDenied("Atendimento indisponível.")
    require_patient_access(
        clinic_id=clinic_id,
        actor=actor,
        patient_id=encounter.patient_id,
        capability=capability,
        consent=consent,
    )
