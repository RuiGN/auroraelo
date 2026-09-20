"""Interface legada bloqueada: chaves sem tenant/autor não são confiáveis.

Rascunhos novos usam persistência SQL com paciente e autor verificados.
Não ler, importar, limpar nem reaproveitar automaticamente o Redis legado.
"""

from django.core.exceptions import PermissionDenied


def get_redis_client():
    raise PermissionDenied("Armazenamento legado sem autorização indisponível.")


class TwelveStepsRedisService:
    @staticmethod
    def _disabled(*args, **kwargs):
        raise PermissionDenied("Operação legada sem ator e clínica bloqueada.")

    save_step_draft = _disabled
    get_session_draft = _disabled
    clear_draft = _disabled
    record_craving_spike = _disabled
    get_active_craving_alert = _disabled
