"""Settings for local development with PostgreSQL."""

import os

from .base import (  # noqa: F401
    ACCOUNT_SESSION_ABSOLUTE_SECONDS,
    ACCOUNT_SESSION_IDLE_SECONDS,
    ASGI_APPLICATION,
    AUDIT_RETENTION_DAYS,
    AUTH_PASSWORD_VALIDATORS,
    AUTH_USER_MODEL,
    BASE_DIR,
    CACHES,
    CLINICAL_OPERATIONS_ENABLED,
    CONSENT_REVOCATION_DESTINATIONS,
    CONTENT_SECURITY_POLICY,
    DEFAULT_AUTO_FIELD,
    DEFAULT_FROM_EMAIL,
    INSTALLED_APPS,
    LANGUAGE_CODE,
    LOCALE_PATHS,
    LOGGING,
    LOGIN_RATE_LIMIT_ATTEMPTS,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    LOGIN_URL,
    MAILERS,
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
    STATIC_ROOT,
    STATIC_URL,
    STATICFILES_DIRS,
    TEMPLATES,
    TIME_ZONE,
    USE_I18N,
    USE_TZ,
    WSGI_APPLICATION,
    environment_flag,
    postgres_database_from_environment,
    required_environment,
)

SECRET_KEY = required_environment("DJANGO_SECRET_KEY")
AUDIT_INTEGRITY_KEY = required_environment("AUDIT_INTEGRITY_KEY")
MASTER_USER_EMAIL = required_environment("MASTER_USER_EMAIL")
MASTER_USER_PASSWORD = required_environment("MASTER_USER_PASSWORD")
DEBUG = True
# Local acceptance exposes draft catalogs; production keeps its reviewed allowlist.
LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]"
    ).split(",")
    if host.strip()
]
DATABASES = {"default": postgres_database_from_environment()}
ALLOW_DEMO_SEED = environment_flag("DJANGO_ALLOW_DEMO_SEED")

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
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
