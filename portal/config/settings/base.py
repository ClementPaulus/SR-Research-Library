"""Base settings shared by every environment.

Every deployment input listed in docs/PORTAL_OPERATIONS.md is read from the
environment here and validated by ``config.checks`` at startup. No credential
is ever defaulted to a real value.
"""

from __future__ import annotations

import os
from pathlib import Path

import dj_database_url

PORTAL_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = PORTAL_DIR.parent


def env(name: str, default=None, required: bool = False):
    value = os.environ.get(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return str(env(name, str(default))).lower() in ("1", "true", "yes", "on")


def env_list(name: str, default: str = "") -> list:
    return [item.strip() for item in str(env(name, default)).split(",") if item.strip()]


# --------------------------------------------------------------------------- core
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-development-only-key-change-me")
DEBUG = False
ALLOWED_HOSTS = env_list("PORTAL_ALLOWED_HOSTS", "localhost,127.0.0.1")
PORTAL_PUBLIC_BASE_URL = env("PORTAL_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
CSRF_TRUSTED_ORIGINS = env_list("PORTAL_CSRF_TRUSTED_ORIGINS", PORTAL_PUBLIC_BASE_URL)
SITE_ID = 1
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "core",
    "accounts",
    "catalog",
    "submissions",
    "registry_bridge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [PORTAL_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "core.context_processors.portal",
    ]},
}]

# --------------------------------------------------------------------------- database
DATABASES = {"default": dj_database_url.config(
    default=env("DATABASE_URL", f"sqlite:///{PORTAL_DIR / 'portal-dev.sqlite3'}"),
    conn_max_age=int(env("DATABASE_CONN_MAX_AGE", "60")),
    conn_health_checks=True,
)}

# --------------------------------------------------------------------------- accounts
AUTH_USER_MODEL = "accounts.Account"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/workspace/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_ADAPTER = "accounts.adapter.PortalAccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = False
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_SESSION_REMEMBER = None  # the user chooses "keep me signed in"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Structura Reditus Research Library] "
ACCOUNT_FORMS = {"signup": "accounts.forms.PortalSignupForm"}
ACCOUNT_RATE_LIMITS = {
    "login_failed": "10/m/ip,5/5m/key",
    "signup": "20/m/ip",
    "reset_password": "20/m/ip,5/m/key",
    "confirm_email": "1/3m/key",
}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = int(env("PORTAL_SESSION_COOKIE_AGE", str(14 * 24 * 3600)))

# --------------------------------------------------------------------------- email
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_FILE_PATH = env("EMAIL_FILE_PATH", str(PORTAL_DIR / "captured-mail"))  # filebased backend only (dev/acceptance)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "library@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --------------------------------------------------------------------------- static & storage
STATIC_URL = "/static/"
STATIC_ROOT = env("PORTAL_STATIC_ROOT", str(PORTAL_DIR / "staticfiles"))
STATICFILES_DIRS = [PORTAL_DIR / "static"]
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Uploads are private: never served from a public MEDIA_URL. Downloads go through authorized views.
PORTAL_STORAGE_BACKEND = env("PORTAL_STORAGE_BACKEND", "filesystem")  # filesystem | s3
PORTAL_MEDIA_ROOT = env("PORTAL_MEDIA_ROOT", str(PORTAL_DIR / "private-media"))
if PORTAL_STORAGE_BACKEND == "s3":
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET", required=True),
            "endpoint_url": env("S3_ENDPOINT_URL") or None,
            "region_name": env("S3_REGION", "us-east-1"),
            "access_key": env("S3_ACCESS_KEY_ID"),
            "secret_key": env("S3_SECRET_ACCESS_KEY"),
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": int(env("S3_SIGNED_URL_SECONDS", "300")),
            "file_overwrite": False,
        },
    }
else:
    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": PORTAL_MEDIA_ROOT, "base_url": None},
    }
PORTAL_UPLOAD_MAX_FILE_BYTES = int(env("PORTAL_UPLOAD_MAX_FILE_BYTES", str(50 * 1024 * 1024)))
PORTAL_UPLOAD_MAX_SUBMISSION_BYTES = int(env("PORTAL_UPLOAD_MAX_SUBMISSION_BYTES", str(200 * 1024 * 1024)))
PORTAL_ARCHIVE_MAX_MEMBERS = int(env("PORTAL_ARCHIVE_MAX_MEMBERS", "200"))
PORTAL_ARCHIVE_MAX_EXPANDED_BYTES = int(env("PORTAL_ARCHIVE_MAX_EXPANDED_BYTES", str(200 * 1024 * 1024)))
PORTAL_ARCHIVE_MAX_DEPTH = int(env("PORTAL_ARCHIVE_MAX_DEPTH", "3"))
PORTAL_EXTRACTION_TIME_BUDGET_SECONDS = int(env("PORTAL_EXTRACTION_TIME_BUDGET_SECONDS", "120"))
PORTAL_URL_FETCH_MAX_BYTES = int(env("PORTAL_URL_FETCH_MAX_BYTES", str(50 * 1024 * 1024)))
PORTAL_URL_FETCH_TIMEOUT_SECONDS = int(env("PORTAL_URL_FETCH_TIMEOUT_SECONDS", "20"))
PORTAL_URL_FETCH_MAX_REDIRECTS = int(env("PORTAL_URL_FETCH_MAX_REDIRECTS", "3"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640
PORTAL_EXTRACTION_MODEL_SERVICE_URL = env("PORTAL_EXTRACTION_MODEL_SERVICE_URL", "")
PORTAL_EXTRACTION_MODEL_VERSION = env("PORTAL_EXTRACTION_MODEL_VERSION", "")

# --------------------------------------------------------------------------- background jobs
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = int(env("PORTAL_JOB_TIME_LIMIT_SECONDS", "900"))
CELERY_WORKER_CONCURRENCY = int(env("PORTAL_WORKER_CONCURRENCY", "2"))
PORTAL_JOB_LEASE_SECONDS = int(env("PORTAL_JOB_LEASE_SECONDS", "600"))
PORTAL_JOB_MAX_ATTEMPTS = int(env("PORTAL_JOB_MAX_ATTEMPTS", "6"))
PORTAL_RECONCILE_INTERVAL_SECONDS = int(env("PORTAL_RECONCILE_INTERVAL_SECONDS", "120"))

# --------------------------------------------------------------------------- registry & GitHub
PORTAL_REGISTRY_REPO_PATH = Path(env("PORTAL_REGISTRY_REPO_PATH", str(REPO_ROOT)))
PORTAL_REGISTRY_DEFAULT_BRANCH = env("PORTAL_REGISTRY_DEFAULT_BRANCH", "main")
PORTAL_REGISTRY_REMOTE = env("PORTAL_REGISTRY_REMOTE", "origin")
PORTAL_REGISTRY_USE_LOCAL_HEAD = env_bool("PORTAL_REGISTRY_USE_LOCAL_HEAD", False)  # dev: evaluate against the local checkout's HEAD
PORTAL_EVALUATION_PYTHON = env("PORTAL_EVALUATION_PYTHON", "")  # defaults to sys.executable
GITHUB_REPO_OWNER = env("GITHUB_REPO_OWNER", "")
GITHUB_REPO_NAME = env("GITHUB_REPO_NAME", "")
GITHUB_APP_ID = env("GITHUB_APP_ID", "")
GITHUB_APP_INSTALLATION_ID = env("GITHUB_APP_INSTALLATION_ID", "")
GITHUB_APP_PRIVATE_KEY_PATH = env("GITHUB_APP_PRIVATE_KEY_PATH", "")
GITHUB_APP_PRIVATE_KEY = env("GITHUB_APP_PRIVATE_KEY", "")  # PEM text from the secret manager (alternative to the path)
GITHUB_WEBHOOK_SECRET = env("GITHUB_WEBHOOK_SECRET", "")
GITHUB_REQUIRED_CHECK = env("GITHUB_REQUIRED_CHECK", "validate")
GITHUB_MERGE_METHOD = env("GITHUB_MERGE_METHOD", "squash")
GITHUB_API_URL = env("GITHUB_API_URL", "https://api.github.com")
PORTAL_GITHUB_ADAPTER = env("PORTAL_GITHUB_ADAPTER", "registry_bridge.github_app.GitHubAppClient")
PORTAL_FAKE_GITHUB_OUTAGE_FILE = env("PORTAL_FAKE_GITHUB_OUTAGE_FILE", "")  # test double only: simulate an outage while this file exists
PORTAL_AUTO_MERGE_ROUTINE = env_bool("PORTAL_AUTO_MERGE_ROUTINE", True)
PORTAL_ADMIN_BOOTSTRAP_EMAIL = env("PORTAL_ADMIN_BOOTSTRAP_EMAIL", "")
PORTAL_SUPPORT_CONTACT = env("PORTAL_SUPPORT_CONTACT", "")

# --------------------------------------------------------------------------- logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"kv": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "kv"}},
    "root": {"handlers": ["console"], "level": env("PORTAL_LOG_LEVEL", "INFO")},
    "loggers": {"django.security": {"level": "WARNING"}, "portal": {"level": env("PORTAL_LOG_LEVEL", "INFO")}},
}
