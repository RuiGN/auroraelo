"""Leituras de sessões mobile (sem efeitos colaterais)."""

from __future__ import annotations

from uuid import UUID

from core.selectors import Selector as Selector

from .models import MobileSession


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
