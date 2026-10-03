#!/bin/bash
# Roteiro ponta a ponta em ambiente fiel ao de produção (local, descartável):
#   PostgreSQL 17 + Redis 8 (compose.test.yml), settings de PRODUÇÃO, gunicorn com 3
#   processos (como o Dockerfile) e um servidor SMTP de captura para os e-mails reais.
#
#   cd mobile/posalta && bash tests/e2e/run-staging.sh      # ou: npm run test:e2e:staging
#
# Com E2E_SERVE_ONLY=1 não roda o Jest: deixa o ambiente de pé (para testar o app num
# simulador ou aparelho), imprime o código de convite lido do e-mail e espera Ctrl-C.
#
# Precisa de Docker com as imagens postgres:17-alpine e redis:8-alpine. Nada persiste:
# os serviços usam tmpfs e são derrubados no fim. Variáveis: E2E_PROJECT, E2E_PY,
# E2E_PORT, E2E_SMTP_PORT.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACK="${E2E_PROJECT:-$(cd "$APP_DIR/../.." && pwd)}"
PY="${E2E_PY:-$BACK/.venv/bin/python}"
PORT="${E2E_PORT:-8766}"
SMTP_PORT="${E2E_SMTP_PORT:-1026}"
WORK="$(mktemp -d)"
COMPOSE=(docker compose -f "$BACK/compose.test.yml")

cleanup() {
  [ -f "$WORK/server.pid" ] && kill "$(cat "$WORK/server.pid")" 2>/dev/null || true
  [ -f "$WORK/sink.pid" ] && kill "$(cat "$WORK/sink.pid")" 2>/dev/null || true
  "${COMPOSE[@]}" down -v > /dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "Subindo PostgreSQL e Redis descartáveis…"
"${COMPOSE[@]}" up -d --wait postgres redis > "$WORK/compose.log" 2>&1

rand() { "$PY" -c "import secrets,sys;print(secrets.token_urlsafe(int(sys.argv[1])))" "$1"; }
fernet() { "$PY" -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"; }

export DJANGO_SETTINGS_MODULE=config.settings.production
export E2E_SETTINGS=config.settings.production
export DJANGO_SECRET_KEY="$(rand 64)"
export AUDIT_INTEGRITY_KEY="$(rand 48)"
export MFA_ENCRYPTION_KEY="$(fernet)"
export MASTER_USER_EMAIL="master.e2e@example.test"
export MASTER_USER_PASSWORD="$(rand 24)"
export DB_NAME=auroraelo DB_USER=auroraelo DB_PASSWORD=auroraelo-test-only
export DB_HOST=127.0.0.1 DB_PORT=55439 DB_SSLMODE=disable
export CACHE_REDIS_URL=redis://127.0.0.1:56389/1
export DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
export DJANGO_SECURE_SSL_REDIRECT=false
export MAILER_BACKEND=django.core.mail.backends.smtp.EmailBackend
export MAILER_HOST=127.0.0.1 MAILER_PORT="$SMTP_PORT"
export DEFAULT_FROM_EMAIL=no-reply@auroraelo.test
export E2E_OUT="$WORK" E2E_MAIL="$WORK/mail.jsonl" E2E_INVITE_VIA=email

echo "Aplicando migrações no PostgreSQL…"
(cd "$BACK" && "$PY" manage.py migrate --noinput > "$WORK/migrate.log" 2>&1)

"$PY" "$APP_DIR/tests/e2e/smtp_sink.py" "$SMTP_PORT" "$E2E_MAIL" > "$WORK/sink.log" 2>&1 &
echo $! > "$WORK/sink.pid"

cp "$APP_DIR"/tests/e2e/seed.py "$APP_DIR"/tests/e2e/seed2.py "$WORK/"
(cd "$BACK" && E2E_RUN="$(( $(date +%s) % 100000 ))" "$PY" "$WORK/seed.py" 2>&1 | grep -v '^{"timestamp"')

( cd "$BACK" && exec "$PY" -m gunicorn config.wsgi:application --bind "127.0.0.1:$PORT" \
    --workers 3 --timeout 120 ) > "$WORK/server.log" 2>&1 &
echo $! > "$WORK/server.pid"
for _ in $(seq 1 40); do
  curl -fsS "http://127.0.0.1:$PORT/health/live/" > /dev/null 2>&1 && break
  sleep 1
done

if [ "${E2E_SERVE_ONLY:-0}" = "1" ]; then
  CODE="$(for _ in $(seq 1 50); do
    c="$("$PY" - "$E2E_MAIL" <<'PYEOF'
import json, re, sys
try:
    for line in open(sys.argv[1], encoding="utf-8"):
        m = re.search(r"copie o código abaixo no aplicativo: (\S+)", json.loads(line)["body"])
        if m:
            print(m.group(1)); break
except FileNotFoundError:
    pass
PYEOF
)"
    [ -n "$c" ] && { echo "$c"; break; }; sleep 0.2; done)"
  echo "Ambiente de pé em http://127.0.0.1:$PORT (logs: $WORK)"
  echo "Código de ativação (veio por e-mail): $CODE"
  echo "Depois de ativar no app, para criar meta, pedido de acesso etc.:"
  echo "  (cd $BACK && E2E_OUT=$WORK $PY $WORK/seed2.py)"
  echo "Ctrl-C encerra e derruba tudo."
  wait "$(cat "$WORK/server.pid")" || true
  exit 0
fi

cd "$APP_DIR"
E2E_BASE_URL="http://127.0.0.1:$PORT" E2E_PROJECT="$BACK" E2E_PY="$PY" TZ=America/Sao_Paulo \
  npx jest --config jest.e2e.config.js --runInBand || status=$?
echo "Logs do ambiente: $WORK"
exit "${status:-0}"
