"""Development settings: local services only, captured email, eager or Redis-backed jobs."""

from .base import *  # noqa: F401,F403
from .base import env, env_bool

DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = ALLOWED_HOSTS + ["0.0.0.0", "web"]  # noqa: F405
# Development email is captured by a local viewer (Mailpit) or the console; it is never real delivery.
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
PORTAL_DEVELOPMENT_EMAIL_CAPTURE = True
PORTAL_REGISTRY_USE_LOCAL_HEAD = env_bool("PORTAL_REGISTRY_USE_LOCAL_HEAD", True)
