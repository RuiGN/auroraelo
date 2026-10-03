"""Fase 2 (depois da ativação): o que só existe quando o paciente já tem conta.

Meta com etapas (o paciente cria), registro "confirmar antes" e o pedido de acesso do
terapeuta (a equipe pede; o paciente responde no app).
"""
import json
import os
import sys
from uuid import UUID, uuid4

sys.path.insert(0, os.getcwd())
import django

django.setup()

from accounts.models import User
from goals import services as goal_services
from journal import services as journal_services
from content.models import Content, ContentRecommendation

seed = json.load(open(os.path.join(os.environ["E2E_OUT"], "seed.json")))
clinic_id = UUID(seed["clinic_id"])
profile_id = UUID(seed["patient_profile_id"])
patient = User.objects.get(email=seed["email"])
therapist = User.objects.get(pk=seed["therapist_id"])
goal_services.create_goal(
    clinic_id=clinic_id, actor=patient, request_id=uuid4(), title="Caminhar três vezes",
    description="Pela vizinhança", horizon="short", priority=2, due_date=None,
    steps=["Escolher o trajeto", "Caminhar na segunda"], visibility="private",
)
entry = journal_services.create_journal_entry(
    clinic_id=clinic_id, actor=patient, patient_profile_id=profile_id,
    mood=3, emotions=[], intensity=2, context="Dia difícil", triggers="", reactions="",
    strategies="", visibility="confirmation_required", request_id=uuid4(),
)
journal_services.request_journal_entry_access(
    clinic_id=clinic_id, therapist=therapist, journal_entry_id=entry.pk,
    purpose="Conversar sobre este dia na sessão", expires_at=None, request_id=uuid4(),
)
print("seed2 ok")

chosen = Content.objects.for_clinic(clinic_id).get(slug="indicado")
ContentRecommendation.infrastructure_objects.create(
    clinic_id=clinic_id, content_id=chosen.pk, recommended_by_id=therapist.pk,
    patient_id=patient.pk, objective="Dormir melhor", priority="high", status="active",
    credential_snapshot={}, credential_digest="x",
)
print("recomendação ok")
