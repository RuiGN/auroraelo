"""Somente testes: herda configuração hermética, sem carregar .env."""

from config.settings.test import *  # noqa: F403
from config.settings.test import INSTALLED_APPS

INSTALLED_APPS = [*INSTALLED_APPS]
if "clinical_operations.apps.ClinicalOperationsConfig" not in INSTALLED_APPS:
    INSTALLED_APPS.append("clinical_operations.apps.ClinicalOperationsConfig")
ROOT_URLCONF = "clinical_operations.testing_urls"
CLINICAL_OPERATIONS_ENABLED = True
