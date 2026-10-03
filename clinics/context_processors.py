"""Safe shared template context for tenant-aware navigation."""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import ClinicConfiguration
from .policies import ClinicAuthorizationPolicy, has_active_clinic_role
from .selectors import active_web_clinics_for_actor
from .typing import ClinicRequest


def clinic_navigation(request: HttpRequest) -> dict[str, Any]:
    """Expose only the current actor's authorized active clinic choices."""
    clinic_request = cast(ClinicRequest, request)
    if (
        not hasattr(request, "user")
        or not isinstance(request.user, AbstractBaseUser)
        or clinic_request.clinic is None
    ):
        return {
            "active_clinic": None,
            "active_clinic_branding": None,
            "available_clinics": [],
            "can_manage_active_clinic": False,
            "is_therapist": False,
            "is_clinic_admin": False,
            "is_administrative_staff": False,
            "can_read_patients": False,
            "can_use_clinical_modules": False,
            "active_role_labels": [],
            "can_use_aftercare": False,
            "can_manage_aftercare_rules": False,
        }
    branding = (
        ClinicConfiguration.objects.for_clinic(clinic_request.clinic.pk)
        .only("display_name", "logo", "primary_color", "secondary_color")
        .first()
    )
    today = timezone.localdate()
    clinic_id = clinic_request.clinic.pk
    user_id = request.user.pk
    is_admin = has_active_clinic_role(
        clinic_id=clinic_id, user_id=user_id, role="clinic_admin", on_date=today
    )
    is_therapist = has_active_clinic_role(
        clinic_id=clinic_id, user_id=user_id, role="therapist", on_date=today
    )
    is_staff_member = has_active_clinic_role(
        clinic_id=clinic_id,
        user_id=user_id,
        role="administrative_staff",
        on_date=today,
    )
    role_labels = [
        label
        for held, label in (
            (is_admin, _("Administrador da clínica")),
            (is_therapist, _("Terapeuta")),
            (is_staff_member, _("Equipe administrativa")),
        )
        if held
    ]
    return {
        "active_clinic": clinic_request.clinic,
        "active_clinic_branding": branding,
        "available_clinics": active_web_clinics_for_actor(request.user),
        "can_manage_active_clinic": ClinicAuthorizationPolicy().is_allowed(
            request.user,
            clinic_request.clinic,
            "clinic.manage",
        ),
        # O menu é montado pela função da pessoa na clínica ativa. É só conveniência: o
        # servidor autoriza cada rota (docs/authorization-matrix.md).
        "is_therapist": is_therapist,
        "is_clinic_admin": is_admin,
        "is_administrative_staff": is_staff_member,
        # patient.demographics.read: administração, terapeuta e equipe administrativa.
        "can_read_patients": is_admin or is_therapist or is_staff_member,
        # patient.clinical.read é só do terapeuta (psiquiatria, painel profissional).
        "can_use_clinical_modules": is_therapist,
        "active_role_labels": role_labels,
        "can_use_aftercare": ClinicAuthorizationPolicy().is_allowed(
            request.user, clinic_request.clinic, "aftercare.read"
        ),
        "can_manage_aftercare_rules": ClinicAuthorizationPolicy().is_allowed(
            request.user, clinic_request.clinic, "aftercare.rules.manage"
        ),
    }
