from .base import *  # noqa: F403,F401


DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",  # noqa: F405
    }
}
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
CELERY_TASK_ALWAYS_EAGER = True
ASYNC_CONSULTATIONS = False
ASYNC_ADMIN_JOBS = False
