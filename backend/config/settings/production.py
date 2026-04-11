from .base import *  # noqa: F403,F401


DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if not SECRET_KEY or SECRET_KEY == "change-me":  # noqa: F405
    raise RuntimeError("SECRET_KEY must be configured for production.")
