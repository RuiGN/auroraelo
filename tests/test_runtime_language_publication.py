"""Exercise the actual local settings, not an overridden language allowlist."""

import json
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ("language", "title"),
    (
        ("pt-br", "Entrar na plataforma"),
        ("en", "Sign in to the platform"),
        ("es", "Iniciar sesión en la plataforma"),
    ),
)
def test_local_runtime_offers_and_applies_launch_languages(
    language: str, title: str
) -> None:
    environment = {
        "DJANGO_SETTINGS_MODULE": "config.settings.development",
        "DJANGO_SECRET_KEY": "test-only-runtime-secret",
        "AUDIT_INTEGRITY_KEY": "test-only-runtime-audit",
        "DJANGO_ALLOWED_HOSTS": "testserver",
        "DB_NAME": "unused",
        "DB_USER": "unused",
        "DB_PASSWORD": "unused",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "1",
    }
    probe = """
import json
import sys
import django
django.setup()
from django.conf import settings
from django.test import Client
language = sys.argv[1]
client = Client(enforce_csrf_checks=True)
page = client.get('/accounts/login/', HTTP_ACCEPT_LANGUAGE=language)
csrf = client.cookies[settings.CSRF_COOKIE_NAME].value
changed = client.post('/accounts/language/', {
    'language': language,
    'next': '/accounts/login/?next=%2Fworkspace%2F',
}, HTTP_X_CSRFTOKEN=csrf)
reload = client.get('/accounts/login/', HTTP_ACCEPT_LANGUAGE='pt-br')
invalid = client.post('/accounts/language/', {'language': 'fr'}, HTTP_X_CSRFTOKEN=csrf)
no_csrf = Client(enforce_csrf_checks=True).post(
    '/accounts/language/', {'language': language}
)
language_cookie = changed.cookies.get(settings.LANGUAGE_COOKIE_NAME)
print(json.dumps({
    'languages': [code for code, name in settings.LANGUAGES],
    'status': page.status_code,
    'negotiated': page.headers.get('Content-Language'),
    'html': page.content.decode(),
    'post_status': changed.status_code,
    'location': changed.headers.get('Location'),
    'cookie': language_cookie.value if language_cookie else None,
    'reload_language': reload.headers.get('Content-Language'),
    'invalid_status': invalid.status_code,
    'no_csrf_status': no_csrf.status_code,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe, language],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["languages"] == ["pt-br", "en", "es"]
    assert report["status"] == 200
    assert report["negotiated"] == language
    assert f'lang="{language}"' in report["html"]
    assert title in report["html"]
    for code in ("pt-br", "en", "es"):
        assert f'name="language" value="{code}"' in report["html"]
    assert report["post_status"] == 302
    assert report["location"] == "/accounts/login/?next=%2Fworkspace%2F"
    assert report["cookie"] == language
    assert report["reload_language"] == language
    assert report["invalid_status"] == 400
    assert report["no_csrf_status"] == 403
