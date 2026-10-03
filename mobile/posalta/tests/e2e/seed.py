"""Fase 1 do seed do roteiro ponta a ponta: o que a EQUIPE cadastraria no web.

Usa os mesmos serviços de domínio das telas da equipe. Escreve e2e/seed.json com o
código de ativação (o paciente ainda não tem conta: ele ativa pelo app).
"""
import json
import os
import sys
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, os.getcwd())
import django

django.setup()

from django.utils import timezone

from people import services as people_services
from routines.care_plan_models import CarePlanStatus
from tests.aftercare_support import build_stage, make_patient
from tests.test_mobile_api_care import _exercise, _habit, _med, _plan
from tests.test_mobile_api_diary_agenda import _agenda, _therapist_link
from tests.test_mobile_api_support import _content, _document, _verified_therapist

OUT = os.environ["E2E_OUT"]

# Cada rodada do seed usa faixas próprias de sequência (slug da clínica, e-mails).
from itertools import count

import tests.aftercare_support as support
from tests.factories import ClinicFactory, UserFactory

RUN = int(os.environ.get("E2E_RUN", "1"))
support._emails = count(RUN * 1000)
ClinicFactory.reset_sequence(RUN * 1000, force=True)
UserFactory.reset_sequence(RUN * 1000, force=True)

stage = build_stage()
profile = make_patient(stage.clinic, stage.admin, name="Alex Exemplo")
who = SimpleNamespace(profile=profile)

_verified_therapist(stage)
_therapist_link(stage, who)
_agenda(stage)
_med(stage.clinic, who)
_plan(stage, who, CarePlanStatus.ACTIVE)
_habit(stage, who)
_exercise(stage, who)

_content(stage, "geral", "Texto geral sobre sono e rotina. " * 30)
_content(stage, "indicado", "Texto indicado pela equipe. " * 20)

# Documentos vigentes: um obrigatório (termos) e um opcional.
_document(
    stage.clinic,
    stage.admin,
    document_type="terms",
    title="Termos de uso",
    purpose="terms_of_use",
    is_mandatory=True,
    content="Estes são os termos de uso sintéticos do aplicativo.",
)
_document(stage.clinic, stage.admin)

issued = people_services.issue_patient_invitation(
    clinic_id=stage.clinic.pk,
    actor=stage.admin,
    patient_profile_id=profile.pk,
    expires_at=people_services.invitation_expiration_after(days=7),
    request_id=uuid4(),
)
json.dump(
    {
        "code": issued.raw_token,
        "email": profile.email,
        "clinic_id": str(stage.clinic.pk),
        "patient_profile_id": str(profile.pk),
        "therapist_id": str(stage.therapist.pk),
        "admin_id": str(stage.admin.pk),
    },
    open(os.path.join(OUT, "seed.json"), "w"),
)
print("seed ok; código de ativação emitido")
