"""Salvaguardas determinísticas conservadoras; não são triagem ou diagnóstico."""

from __future__ import annotations

import re
from typing import Any

from django.utils.translation import gettext as _

from .recovery_knowledge import normalized

IDENTITY = "Aurora Elo — apoio digital de IA"
_URGENT = re.compile(
    r"suicid|me matar|kill myself|end my life|tirar minha vida|quero morrer|"
    r"want to die|quiero morir|overdose|sobredosis|convuls|seizure|"
    r"abstinencia (?:grave|severa)|severe withdrawal|delirium|alucina|hallucinat|"
    r"nao consigo respirar|can.t breathe|no puedo respirar|desmai|unconscious"
)
_BOUNDARY = re.compile(
    r"diagnost|prescri|receit|posolog|\bdose\b|\bdosis\b|\bdosage\b|"
    r"\b\d+\s*(?:mg|mcg|ml)\b|garant|guarantee|nunca.*recair|"
    r"psicologo humano|human psychologist|sou (?:seu|sua) psicolog|"
    r"ignore.*(?:instruc|instru|previous)|system prompt|developer mode|"
    r"suspend.*medica|stop.*medication"
)


def safety_response(message: str) -> dict[str, Any] | None:
    """Retorna orientação fixa; não aciona atendimento nem registra relato."""
    normalized_message = normalized(message)
    if _URGENT.search(normalized_message):
        code = "urgent_human_help"
        answer = _(
            "Pode ser uma situação urgente. Procure ajuda humana agora. "
            "No Brasil, ligue SAMU 192 ou vá a um serviço de emergência; "
            "se puder, fique acompanhado por alguém de confiança. "
            "Fora do Brasil, use o número de emergência local. "
            "O CVV 188 oferece apoio emocional no Brasil, mas não substitui "
            "emergência médica em overdose ou abstinência grave. "
            "Não ajuste medicamentos nem tente conduzir desintoxicação por este chat. "
            "Este serviço não monitora você e não acionou socorro."
        )
    elif _BOUNDARY.search(normalized_message):
        code = "clinical_boundary"
        answer = _(
            "Sou um apoio digital de IA, não um psicólogo humano. "
            "Não faço diagnóstico, prescrição, orientação de dose ou promessa de "
            "abstinência. Procure um profissional qualificado para essas decisões. "
            "Posso ajudar a localizar conteúdo educativo com fontes e limitações."
        )
    else:
        return None
    return {
        "mode": "safety",
        "code": code,
        "identity": IDENTITY,
        "answer": answer,
        "content_language": "pt-br",
        "sources": [],
        "notifies_emergency_services": False,
    }
