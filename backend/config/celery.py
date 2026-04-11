import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    app = None
else:
    app = Celery("consulta_juridica")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
