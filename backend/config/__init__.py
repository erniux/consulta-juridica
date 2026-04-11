try:
    from .celery import app as celery_app
except Exception:  # pragma: no cover - keeps Django usable without Celery installed.
    celery_app = None


__all__ = ("celery_app",)
