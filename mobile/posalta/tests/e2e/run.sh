#!/bin/bash
# Roteiro ponta a ponta do app contra um servidor Django de verdade.
#
#   cd mobile/posalta && bash tests/e2e/run.sh
#
# Cria um banco SQLite descartável (a primeira migração leva alguns minutos), semeia o
# que a equipe cadastraria (serviços, horários, medicação, plano, documentos…), sobe o
# servidor em 127.0.0.1 e roda tests/e2e/live.e2e.ts com o código real do app.
# Variáveis: E2E_PROJECT (raiz do web), E2E_PY, E2E_WORK (reaproveita o banco), E2E_PORT.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACK="${E2E_PROJECT:-$(cd "$APP_DIR/../.." && pwd)}"
PY="${E2E_PY:-$BACK/.venv/bin/python}"
WORK="${E2E_WORK:-$(mktemp -d)}"
PORT="${E2E_PORT:-8765}"
mkdir -p "$WORK"

export SQLITE_NAME="$WORK/e2e.sqlite3"
export DJANGO_SETTINGS_MODULE=config.settings.test
export E2E_OUT="$WORK"

if [ ! -f "$SQLITE_NAME" ]; then
  echo "Migrando o banco descartável (alguns minutos)…"
  (cd "$BACK" && "$PY" manage.py migrate --noinput > "$WORK/migrate.log" 2>&1)
fi

cp "$APP_DIR"/tests/e2e/seed.py "$APP_DIR"/tests/e2e/seed2.py "$WORK/"
(cd "$BACK" && E2E_RUN="$(( $(date +%s) % 100000 ))" "$PY" "$WORK/seed.py" 2>&1 | grep -v '^{"timestamp"')

# `exec` faz o PID guardado ser o do próprio servidor (e não o de um subshell).
( cd "$BACK" && exec "$PY" manage.py runserver "127.0.0.1:$PORT" --noreload ) > "$WORK/server.log" 2>&1 &
echo $! > "$WORK/server.pid"
cleanup() { kill "$(cat "$WORK/server.pid")" 2>/dev/null || true; }
trap cleanup EXIT
for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:$PORT/health/live/" > /dev/null 2>&1 && break
  sleep 1
done

cd "$APP_DIR"
E2E_BASE_URL="http://127.0.0.1:$PORT" E2E_PROJECT="$BACK" E2E_SQLITE="$SQLITE_NAME" \
  E2E_PY="$PY" TZ=America/Sao_Paulo \
  npx jest --config jest.e2e.config.js --runInBand
