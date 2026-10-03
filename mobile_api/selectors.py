"""Leituras de sessões mobile (sem efeitos colaterais).

As leituras da equipe nunca expõem token, resumo de token, endereço de rede ou o
código de ativação do convite: só rótulo, plataforma, versão e datas de uso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from django.db.models import Max
from django.utils import timezone

from clinics.policies import has_active_clinic_role
from concierge.selectors import discharge_date_for_patient
from core.selectors import Selector as Selector
from people.selectors import PatientInvitationState, patient_invitation_state

from .contracts import PATIENT_ROLE
from .models import MobileSession

# Situação da conta do paciente no app.
ACCOUNT_NOT_ACTIVATED = "not_activated"
ACCOUNT_ACTIVE = "active"
ACCOUNT_ENDED = "ended"


def active_sessions_for_patient(
    *, clinic_id: UUID, user_id: UUID
) -> list[MobileSession]:
    """Aparelhos ativos da própria pessoa, do uso mais recente ao mais antigo."""
    return list(
        MobileSession.objects.for_clinic(clinic_id)
        .active()
        .filter(user_id=user_id)
        .order_by("-last_used_at", "-created_at")
    )


@dataclass(frozen=True, slots=True)
class DeviceRow:
    """Um aparelho conectado, como a equipe o enxerga (sem nenhuma credencial)."""

    session_id: UUID
    device_label: str
    platform: str
    app_version: str
    connected_at: datetime
    last_used_at: datetime


@dataclass(frozen=True, slots=True)
class PatientAppAccess:
    """Resumo do acesso de um paciente ao app para a equipe."""

    patient_profile_id: UUID
    account_state: str
    invitation: PatientInvitationState | None
    devices: tuple[DeviceRow, ...]
    last_access_at: datetime | None
    discharge_date: date | None


def _device_row(session: MobileSession) -> DeviceRow:
    return DeviceRow(
        session_id=session.pk,
        device_label=session.device_label,
        platform=session.platform,
        app_version=session.app_version,
        connected_at=session.created_at,
        last_used_at=session.last_used_at,
    )


def connected_devices(*, clinic_id: UUID, patient_profile_id: UUID) -> list[DeviceRow]:
    """Aparelhos com sessão ativa do paciente, do uso mais recente ao mais antigo."""
    sessions = (
        MobileSession.objects.for_clinic(clinic_id)
        .active()
        .filter(patient_profile_id=patient_profile_id)
        .order_by("-last_used_at", "-created_at")
    )
    return [_device_row(session) for session in sessions]


def connected_device(
    *, clinic_id: UUID, patient_profile_id: UUID, session_id: UUID
) -> DeviceRow | None:
    """Um aparelho ativo, só se pertencer ao paciente e à clínica informados."""
    session = (
        MobileSession.objects.for_clinic(clinic_id)
        .active()
        .filter(patient_profile_id=patient_profile_id, pk=session_id)
        .first()
    )
    return _device_row(session) if session is not None else None


def last_app_access(*, clinic_id: UUID, patient_profile_id: UUID) -> datetime | None:
    """Último uso do app por qualquer aparelho, inclusive os já encerrados.

    Sessões encerradas ou vencidas há mais de 30 dias são apagadas pela rotina de
    retenção; sem registro restante, não há acesso a informar.
    """
    value = (
        MobileSession.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=patient_profile_id)
        .aggregate(latest=Max("last_used_at"))["latest"]
    )
    return value if isinstance(value, datetime) else None


def _account_state(
    *, clinic_id: UUID, patient_user_id: UUID | None, on_date: date
) -> str:
    if patient_user_id is None:
        return ACCOUNT_NOT_ACTIVATED
    if has_active_clinic_role(
        clinic_id=clinic_id,
        user_id=patient_user_id,
        role=PATIENT_ROLE,
        on_date=on_date,
    ):
        return ACCOUNT_ACTIVE
    return ACCOUNT_ENDED


def patient_app_access(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    patient_user_id: UUID | None,
) -> PatientAppAccess:
    """Convite, conta, aparelhos, último acesso e data da alta de um paciente."""
    return PatientAppAccess(
        patient_profile_id=patient_profile_id,
        account_state=_account_state(
            clinic_id=clinic_id,
            patient_user_id=patient_user_id,
            on_date=timezone.localdate(),
        ),
        invitation=patient_invitation_state(
            clinic_id=clinic_id, patient_profile_id=patient_profile_id
        ),
        devices=tuple(
            connected_devices(
                clinic_id=clinic_id, patient_profile_id=patient_profile_id
            )
        ),
        last_access_at=last_app_access(
            clinic_id=clinic_id, patient_profile_id=patient_profile_id
        ),
        discharge_date=discharge_date_for_patient(
            clinic_id=clinic_id, patient_profile_id=patient_profile_id
        ),
    )
