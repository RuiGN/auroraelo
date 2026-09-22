#!/bin/sh
set -e

echo "Waiting for PostgreSQL database at ${DB_HOST:-db}:${DB_PORT:-5432}..."
until python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('${DB_HOST:-db}', int('${DB_PORT:-5432}')))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
  echo "PostgreSQL is not ready yet. Retrying in 2 seconds..."
  sleep 2
done
echo "PostgreSQL is available and accepting connections."

if [ "$1" = "gunicorn" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput

  echo "Collecting static files..."
  python manage.py collectstatic --noinput

  if [ "${DJANGO_ALLOW_DEMO_SEED}" = "true" ] || [ "${DJANGO_ALLOW_DEMO_SEED}" = "1" ]; then
    echo "Running clinical seed command..."
    python manage.py seed_psychiatry || true
  fi

  echo "Ensuring master superuser exists..."
  python manage.py shell -c "
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()
email = getattr(settings, 'MASTER_USER_EMAIL', 'master@auroraelo.internal')
password = getattr(settings, 'MASTER_USER_PASSWORD', 'master')
qs = User.objects.filter(email=email)
if not qs.exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Master',
        last_name='Admin',
    )
    print(f'Master user created: {email}')
else:
    print(f'Master user already exists: {email}')
" || true
fi

echo "Starting Aurora Elo application with command: $@"
exec "$@"
