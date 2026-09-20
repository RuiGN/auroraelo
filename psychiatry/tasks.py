"""Compatibilidade com mensagens antigas: tarefas sem ator/tenant desativadas.

Não consultar prontuários, gerar planos, usar provedores ou afirmar delivery.
Novas operações síncronas autorizadas vivem em psychiatry.services.
"""

from celery import shared_task


@shared_task
def generate_ai_relapse_prevention_plan_task(*args, **kwargs):
    return {"status": "disabled", "ai_processed": False}


@shared_task
def consolidate_twelve_steps_task(*args, **kwargs):
    return {"status": "disabled", "persisted": False, "ai_processed": False}


@shared_task
def notify_urgent_craving_alert_task(*args, **kwargs):
    return {
        "status": "disabled",
        "notification_delivered": False,
        "monitoring_active": False,
    }
