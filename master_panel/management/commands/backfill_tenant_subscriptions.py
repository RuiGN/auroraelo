"""Backfill neutral commercial state for infrastructure clinics."""

from django.core.management.base import BaseCommand

from master_panel.tenant_services import backfill_tenant_subscriptions


class Command(BaseCommand):
    """Create only missing free/trial subscription rows."""

    help = "Garante uma assinatura inicial neutra para cada clínica."

    def handle(self, *args: object, **options: object) -> str:
        created = backfill_tenant_subscriptions()
        message = f"Assinaturas neutras criadas: {created}."
        self.stdout.write(self.style.SUCCESS(message))
        return message
