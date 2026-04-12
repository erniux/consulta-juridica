import importlib.util
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BASE_DIR.parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


for candidate in (REPO_DIR / ".env", BASE_DIR / ".env"):
    load_env_file(candidate)


def env(key: str, default=None):
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    value = env(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    value = env(key, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


DEBUG = env_bool("DEBUG", True)
SECRET_KEY = env("SECRET_KEY", "change-me")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver,backend")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
]

if module_available("corsheaders"):
    INSTALLED_APPS.append("corsheaders")

if module_available("django_celery_results"):
    INSTALLED_APPS.append("django_celery_results")

INSTALLED_APPS += [
    "apps.accounts",
    "apps.legal_sources",
    "apps.legal_documents",
    "apps.legal_indexing",
    "apps.consultations",
    "apps.llm_orchestrator",
    "apps.citations",
    "apps.admin_panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
]

if module_available("whitenoise"):
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

if module_available("corsheaders"):
    MIDDLEWARE.append("corsheaders.middleware.CorsMiddleware")

MIDDLEWARE += [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

#DATABASE_ENGINE = env("DB_ENGINE", "postgresql")
#if DATABASE_ENGINE == "sqlite":
#    DATABASES = {
#        "default": {
#            "ENGINE": "django.db.backends.sqlite3",
#            "NAME": BASE_DIR / "db.sqlite3",
#        }
#    }
#else:
#    DATABASES = {
#        "default": {
#            "ENGINE": "django.db.backends.postgresql",
#            "NAME": env("DB_NAME", "consulta_juridica"),
#            "USER": env("DB_USER", "postgres"),
#            "PASSWORD": env("DB_PASSWORD", "postgres"),
#            "HOST": env("DB_HOST", "db"),
#            "PORT": env("DB_PORT", "5432"),
#        }
#    }

database_url = env("DATABASE_URL")

if database_url:
    parsed = urlparse(database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or "5432",
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }
else:
    DATABASE_ENGINE = env("DB_ENGINE", "postgresql")
    if DATABASE_ENGINE == "sqlite":
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": env("DB_NAME", "consulta_juridica"),
                "USER": env("DB_USER", "postgres"),
                "PASSWORD": env("DB_PASSWORD", "postgres"),
                "HOST": env("DB_HOST", "db"),
                "PORT": env("DB_PORT", "5432"),
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = env("TIME_ZONE", "America/Mexico_City")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://frontend:5173",
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REDIS_URL = env("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_TRACK_STARTED = True
CELERY_TIMEZONE = TIME_ZONE

APP_NAME = "Consulta Juridica Laboral MX"
APP_DISCLAIMER = (
    "La respuesta es informativa y no sustituye asesoria legal profesional ni "
    "representacion juridica."
)
LLM_PROVIDER = env("LLM_PROVIDER", "mock")
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "mock-embedding-v1")
CHAT_MODEL = env("CHAT_MODEL", "mock-legal-chat-v1")
VECTOR_DIMENSIONS = int(env("VECTOR_DIMENSIONS", "16"))
ASYNC_CONSULTATIONS = env_bool("ASYNC_CONSULTATIONS", False)
ASYNC_ADMIN_JOBS = env_bool("ASYNC_ADMIN_JOBS", False)
DEFAULT_RETRIEVAL_LIMIT = int(env("DEFAULT_RETRIEVAL_LIMIT", "6"))
AUTO_SYNC_JURISPRUDENCE_ON_CONSULTATION = env_bool(
    "AUTO_SYNC_JURISPRUDENCE_ON_CONSULTATION",
    False,
)
AUTO_SYNC_JURISPRUDENCE_MAX_RESULTS = int(
    env("AUTO_SYNC_JURISPRUDENCE_MAX_RESULTS", "5")
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", "INFO"),
    },
}
