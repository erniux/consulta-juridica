#!/bin/sh
set -e

cd /app/backend
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver 0.0.0.0:8000
