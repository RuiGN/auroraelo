"""Sincroniza somente corpus educativo público, com leitura de confirmação."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.translation import gettext as _

from ai_assistant.recovery_knowledge import (
    MAX_CORPUS_BYTES,
    KnowledgeUnavailableError,
    load_corpus,
    read_corpus,
    redis_client,
    sync_corpus,
)


class Command(BaseCommand):
    help = "Sincroniza corpus público em Redis HASH dedicado, sem ativar IA."
    requires_system_checks: list[str] = []

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--corpus", required=True, help="Arquivo JSON público revisado"
        )
        parser.add_argument(
            "--verify", action="store_true", help="Verificação adicional"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            with Path(options["corpus"]).open("rb") as stream:
                corpus = load_corpus(stream.read(MAX_CORPUS_BYTES + 1))
            with redis_client() as client:
                created = sync_corpus(client, corpus)
                if options["verify"] and read_corpus(client, corpus.version) != corpus:
                    raise KnowledgeUnavailableError
        except (OSError, ValueError, KnowledgeUnavailableError) as exc:
            raise CommandError(
                _("Não foi possível sincronizar/verificar o corpus.")
            ) from exc
        self.stdout.write(
            json.dumps(
                {
                    "version": corpus.version,
                    "sha256": corpus.sha256,
                    "source_count": len(corpus.sources),
                    "created": created,
                    "verified": True,
                }
            )
        )
