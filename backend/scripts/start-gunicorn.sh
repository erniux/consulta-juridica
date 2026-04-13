#!/usr/bin/env sh
set -e

cd "$(dirname "$0")/.."

if [ "${AUTO_RUN_MIGRATIONS:-true}" = "true" ]; then
  python manage.py migrate --noinput
fi

if [ "${AUTO_RUN_COLLECTSTATIC:-true}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

if [ "${BOOTSTRAP_LEGAL_DATA:-false}" = "true" ]; then
  python manage.py seed_demo_data
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
