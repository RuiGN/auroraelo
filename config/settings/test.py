"""Hermetic settings for automated tests."""

import os
from typing import Any

from .base import (  # noqa: F401
    ACCOUNT_SESSION_ABSOLUTE_SECONDS,
    ACCOUNT_SESSION_IDLE_SECONDS,
    ASGI_APPLICATION,
    AUDIT_RETENTION_DAYS,
    AUTH_PASSWORD_VALIDATORS,
    AUTH_USER_MODEL,
    BASE_DIR,
    CACHES,
    CONSENT_REVOCATION_DESTINATIONS,
    CONTENT_SECURITY_POLICY,
    DEFAULT_AUTO_FIELD,
    DEFAULT_FROM_EMAIL,
    INSTALLED_APPS,
    JAZZMIN_SETTINGS,
    JAZZMIN_UI_TWEAKS,
    LANGUAGE_CODE,
    LOCALE_PATHS,
    LOGGING,
    LOGIN_RATE_LIMIT_ATTEMPTS,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    LOGIN_URL,
    MEDIA_ROOT,
    MEDIA_URL,
    MFA_ENCRYPTION_KEY,
    MIDDLEWARE,
    PASSWORD_RECOVERY_RATE_LIMIT_ATTEMPTS,
    PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS,
    PASSWORD_RESET_TIMEOUT,
    PERMISSIONS_POLICY,
    PRIVACY_EXPORT_TTL_SECONDS,
    PRIVACY_LIFECYCLE_DESTINATIONS,
    PRIVACY_REAUTH_MAX_AGE_SECONDS,
    PRIVACY_REQUEST_DUE_DAYS,
    PRIVATE_MEDIA_ROOT,
    PRIVATE_UPLOAD_MALWARE_SCAN_COMMAND,
    RECOVERY_AI_CLINICAL_APPROVED,
    RECOVERY_AI_ENABLED,
    RECOVERY_CONSENT_RESOLVER,
    REFERRER_POLICY,
    ROOT_URLCONF,
    SENSITIVE_REAUTH_RATE_LIMIT_ATTEMPTS,
    SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS,
    STATIC_ROOT,
    STATIC_URL,
    STATICFILES_DIRS,
    TEMPLATES,
    TIME_ZONE,
    USE_I18N,
    USE_TZ,
    WSGI_APPLICATION,
    postgres_database_from_environment,
)

SECRET_KEY = "test-only-not-a-secret"
AUDIT_INTEGRITY_KEY = "test-audit-integrity-key-with-32-characters-minimum"
MASTER_USER_EMAIL = "master.test@example.test"
MASTER_USER_PASSWORD = "test-master-password-only"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
DATABASES: dict[str, Any]
if os.environ.get("TEST_DATABASE") == "postgresql":
    DATABASES = {"default": postgres_database_from_environment()}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_NAME", ":memory:"),
        }
    }
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Test clients commonly use force_login(), which bypasses the real login service that
# registers managed sessions. Security tests override this to False explicitly.
ACCOUNT_SESSION_ALLOW_UNKNOWN = True
# Use LocMemCache for hermetic unit tests (no Redis required).
# Integration tests with compose.test.yml can set CACHE_REDIS_URL to exercise Redis.
_test_cache_url = os.environ.get("CACHE_REDIS_URL")
if _test_cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _test_cache_url,
            "KEY_PREFIX": "auroraelo-test",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "auroraelo-test",
        }
    }
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CLINICAL_OPERATIONS_ENABLED = False
# Expand the language list in tests so that i18n and translation tests can
# exercise EN and ES without requiring a production launch of those languages.
LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)
