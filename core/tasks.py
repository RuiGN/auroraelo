from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task(name="core.tasks.daily_backup")
def daily_backup():
    """
    Tarefa diária automatizada para realizar o backup do banco de dados,
    criptografar e fazer o upload para o Google Drive.
    """
    logger.info("Iniciando rotina de backup diário via Celery...")
    try:
        call_command("backup_to_drive")
        logger.info("Rotina de backup diário concluída com sucesso.")
    except Exception as e:
        logger.error(f"Falha na rotina de backup diário: {str(e)}", exc_info=True)
        raise
