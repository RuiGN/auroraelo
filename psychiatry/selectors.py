"""Consultas clínicas: tenant e autorização por paciente antes de agregar."""

from django.http import Http404

from consents.services import resolve_purpose_access
from people.policies import PatientAuthorizationPolicy

from .models import PsychiatricPatientProfile
from .policies import require_domain_access


def visible_patients(*, actor, clinic, mode="clinical"):
    require_domain_access(actor=actor, clinic=clinic, mode=mode)
    scoped = PsychiatricPatientProfile.objects.filter(
        clinic_id=clinic.pk,
        user__isnull=False,
        user__is_active=True,
    )
    if mode == "patient":
        return scoped.filter(user_id=actor.pk)
    allowed = []
    policy = PatientAuthorizationPolicy()
    for patient in (
        scoped.select_related("user")
        .only("pk", "user_id", "user__id", "user__is_active")
        .iterator()
    ):
        if (
            policy.is_allowed(
                actor=actor,
                clinic=clinic,
                patient=patient.user,
                action="patient.clinical.read",
                record_is_active=True,
            )
            and resolve_purpose_access(
                clinic_id=clinic.pk,
                subject_id=patient.user_id,
                purpose="clinical_follow_up",
            ).allowed
        ):
            allowed.append(patient.pk)
    return scoped.filter(pk__in=allowed)


def own_patient(*, actor, clinic):
    patients = list(visible_patients(actor=actor, clinic=clinic, mode="patient")[:2])
    if len(patients) != 1:
        raise Http404("Vínculo de paciente indisponível.")
    return patients[0]


def clinical_patient(*, actor, clinic, patient_uuid):
    try:
        return visible_patients(actor=actor, clinic=clinic).get(uuid=patient_uuid)
    except PsychiatricPatientProfile.DoesNotExist as exc:
        raise Http404("Paciente indisponível.") from exc
