#!/usr/bin/env sh
set -e

cd "$(dirname "$0")/.."

python manage.py migrate --noinput

if [ "${AUTO_RUN_COLLECTSTATIC:-true}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

if [ "${BOOTSTRAP_LEGAL_DATA:-false}" = "true" ]; then
  python manage.py seed_demo_data
fi
