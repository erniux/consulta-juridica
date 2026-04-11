#!/usr/bin/env sh
set -e

cd "$(dirname "$0")/.."

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
