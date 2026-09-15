"""Production settings: HTTPS termination upstream, secrets from the secret manager, strict cookies."""

from .base import *  # noqa: F401,F403
from .base import env, env_bool

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)
if SECRET_KEY.startswith("insecure-"):
    raise RuntimeError("DJANGO_SECRET_KEY must come from the secret manager in production")
ALLOWED_HOSTS = env("PORTAL_ALLOWED_HOSTS", required=True).split(",")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("PORTAL_BEHIND_TLS_PROXY", True) else None
USE_X_FORWARDED_HOST = env_bool("PORTAL_BEHIND_TLS_PROXY", True)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(env("PORTAL_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
PORTAL_DEVELOPMENT_EMAIL_CAPTURE = False
if EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":  # noqa: F405
    raise RuntimeError("production requires a real SMTP/API email backend")
if PORTAL_STORAGE_BACKEND != "s3":  # noqa: F405
    raise RuntimeError("production requires S3-compatible object storage (PORTAL_STORAGE_BACKEND=s3)")
