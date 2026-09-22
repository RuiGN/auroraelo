"""Shared settings for every project environment."""

import os
import shlex
from pathlib import Path
from typing import NotRequired, TypedDict

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]


class DatabaseConfig(TypedDict):
    """Shape of a Django PostgreSQL database configuration."""

    ENGINE: str
    NAME: str
    USER: str
    PASSWORD: str
    HOST: str
    PORT: str
    OPTIONS: NotRequired[dict[str, str]]


def required_environment(name: str) -> str:
    """Return a mandatory non-empty environment value or fail clearly."""
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Mandatory environment variable {name} is not set.")
    return value


def postgres_database_from_environment() -> DatabaseConfig:
    """Build an explicit PostgreSQL database configuration."""
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_environment("DB_NAME"),
        "USER": required_environment("DB_USER"),
        "PASSWORD": required_environment("DB_PASSWORD"),
        "HOST": required_environment("DB_HOST"),
        "PORT": required_environment("DB_PORT"),
    }


def environment_flag(name: str, default: bool = False) -> bool:
    """Parse a conventional boolean environment variable."""
    fallback = "true" if default else "false"
    return os.environ.get(name, fallback).lower() in {"1", "true", "yes"}


CLINICAL_OPERATIONS_ENABLED = environment_flag("CLINICAL_OPERATIONS_ENABLED")

# Sem opt-in B2C persistido e revisão clínica, ambiente não ativa esta vertical.
RECOVERY_AI_ENABLED = False
RECOVERY_AI_CLINICAL_APPROVED = False
RECOVERY_CONSENT_RESOLVER = None


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "tenancy.apps.TenancyConfig",
    "accounts.apps.AccountsConfig",
    "clinics.apps.ClinicsConfig",
    "people.apps.PeopleConfig",
    "consents.apps.ConsentsConfig",
    "audit.apps.AuditConfig",
    "privacy.apps.PrivacyConfig",
    "therapist_dashboard.apps.TherapistDashboardConfig",
    "onboarding.apps.OnboardingConfig",
    "journal.apps.JournalConfig",
    "goals.apps.GoalsConfig",
    "scheduling.apps.SchedulingConfig",
    "analytics.apps.AnalyticsConfig",
    "finance.apps.FinanceConfig",
    "content.apps.ContentConfig",
    "integrations.apps.IntegrationsConfig",
    "routines.apps.RoutinesConfig",
    "wellness.apps.WellnessConfig",
    "support_network.apps.SupportNetworkConfig",
    "communities.apps.CommunitiesConfig",
    "medical_records.apps.MedicalRecordsConfig",
    "clinical_operations.apps.ClinicalOperationsConfig",
    "ai_assistant.apps.AiAssistantConfig",
    "psychiatry.apps.PsychiatryConfig",
    "master_panel.apps.MasterPanelConfig",
]

MIDDLEWARE = [
    "core.middleware.RequestCorrelationMiddleware",
    "core.metrics.MetricsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.security.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.UserLanguageMiddleware",
    "clinics.middleware.ClinicTenantMiddleware",
    "master_panel.middleware.PaymentRequiredMiddleware",
    "accounts.middleware.AccountSecurityMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
    "form-action 'self'; object-src 'none'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'"
)
REFERRER_POLICY = "strict-origin-when-cross-origin"
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.language_preferences",
                "clinics.context_processors.clinic_navigation",
                "consents.context_processors.revocation_work_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
DEFAULT_WORKSPACE_LAYOUT = os.environ.get("DEFAULT_WORKSPACE_LAYOUT", "vertical")
LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(
    os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")
)
PASSWORD_RECOVERY_RATE_LIMIT_ATTEMPTS = int(
    os.environ.get("PASSWORD_RECOVERY_RATE_LIMIT_ATTEMPTS", "5")
)
PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS = int(
    os.environ.get("PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS", "900")
)
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", "900"))
ACCOUNT_SESSION_IDLE_SECONDS = int(
    os.environ.get("ACCOUNT_SESSION_IDLE_SECONDS", "1800")
)
ACCOUNT_SESSION_ABSOLUTE_SECONDS = int(
    os.environ.get("ACCOUNT_SESSION_ABSOLUTE_SECONDS", "43200")
)
MFA_ENCRYPTION_KEY = os.environ.get("MFA_ENCRYPTION_KEY", "development-only-mfa-key")
SENSITIVE_REAUTH_RATE_LIMIT_ATTEMPTS = int(
    os.environ.get("SENSITIVE_REAUTH_RATE_LIMIT_ATTEMPTS", "5")
)
SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS = int(
    os.environ.get("SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS", "300")
)
AUDIT_RETENTION_DAYS = int(os.environ.get("AUDIT_RETENTION_DAYS", "2190"))
PRIVACY_REQUEST_DUE_DAYS = int(os.environ.get("PRIVACY_REQUEST_DUE_DAYS", "15"))
PRIVACY_REAUTH_MAX_AGE_SECONDS = int(
    os.environ.get("PRIVACY_REAUTH_MAX_AGE_SECONDS", "600")
)
PRIVACY_EXPORT_TTL_SECONDS = int(os.environ.get("PRIVACY_EXPORT_TTL_SECONDS", "900"))
PRIVACY_LIFECYCLE_DESTINATIONS = {
    "correction": ("primary_database",),
    "revocation": ("external_processor",),
    "erasure": ("primary_database",),
}
CONSENT_REVOCATION_DESTINATIONS = tuple(
    destination.strip()
    for destination in os.environ.get(
        "CONSENT_REVOCATION_DESTINATIONS",
        "clinic_operations",
    ).split(",")
    if destination.strip()
)

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator")},
    {"NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator")},
    {"NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator")},
]

LANGUAGE_CODE = "pt-br"
# Only the reviewed and launched language is active in base/production.
# Development and test environments expand this list via their own settings.
LANGUAGES = (("pt-br", "Português (Brasil)"),)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"
PRIVATE_UPLOAD_MALWARE_SCAN_COMMAND = tuple(
    shlex.split(os.environ.get("PRIVATE_UPLOAD_MALWARE_SCAN_COMMAND", ""))
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("CACHE_REDIS_URL", "redis://redis:6379/1"),
        "KEY_PREFIX": "auroraelo",
    }
}

MAILERS = {
    "default": {
        "BACKEND": os.environ.get(
            "MAILER_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
        ),
        "OPTIONS": {
            "host": os.environ.get("MAILER_HOST", "localhost"),
            "port": int(os.environ.get("MAILER_PORT", "25")),
            "username": os.environ.get("MAILER_USERNAME", ""),
            "password": os.environ.get("MAILER_PASSWORD", ""),
            "use_tls": environment_flag("MAILER_USE_TLS"),
        },
    }
}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "core.observability.JsonLogFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "application": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Celery & Message Broker Configuration (RabbitMQ + Redis)
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Redis State Engine (Real-time 12 Steps Anamnesis & Craving Telemetry)
REDIS_STATE_URL = os.environ.get("REDIS_STATE_URL", "redis://redis:6379/3")

# AI / OpenAI Cognitive Relapse Prevention Plan Generator
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")

# CSRF and Proxy Security Configuration
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://auroraelo.rgnsystems.com.br,http://localhost:4130,http://127.0.0.1:4130,http://localhost:4132,http://127.0.0.1:4132",
    ).split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# ── Stripe Billing ────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY: str = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Map plan slugs to Stripe Price IDs (configure per-environment).
STRIPE_PRICE_IDS: dict[str, str] = {
    "starter": os.environ.get("STRIPE_PRICE_STARTER", ""),
    "professional": os.environ.get("STRIPE_PRICE_PROFESSIONAL", ""),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE", ""),
}

# ── Master Panel ──────────────────────────────────────────────────────────────
# Default password for the auto-created master superuser (override in prod).
MASTER_USER_EMAIL: str = os.environ.get(
    "MASTER_USER_EMAIL", "master@auroraelo.internal"
)
MASTER_USER_PASSWORD: str = os.environ.get("MASTER_USER_PASSWORD", "master")
