"""Remove sessões do app do paciente vencidas ou revogadas há mais de N dias."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from mobile_api.services import purge_finished_sessions


class Command(BaseCommand):
    help = "Remove sessões mobile vencidas ou revogadas há mais de N dias (padrão 30)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args: Any, **options: Any) -> None:
        removed = purge_finished_sessions(retention_days=options["days"])
        self.stdout.write(f"{removed} sessão(ões) removida(s).")
