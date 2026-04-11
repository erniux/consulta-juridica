#!/bin/sh
set -e

cd /app/backend
python manage.py migrate
celery -A config worker -l info
