"""Test settings: isolated database, in-memory email, eager jobs, fake GitHub adapter, temp storage."""

import tempfile

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
SECRET_KEY = "test-only-secret-key-not-for-any-deployment"
DATABASES = {"default": dj_database_url.config(default=env("TEST_DATABASE_URL", "sqlite:///:memory:"))}  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
PORTAL_STORAGE_BACKEND = "filesystem"
PORTAL_MEDIA_ROOT = tempfile.mkdtemp(prefix="portal-test-media-")
STORAGES["default"] = {  # noqa: F405
    "BACKEND": "django.core.files.storage.FileSystemStorage",
    "OPTIONS": {"location": PORTAL_MEDIA_ROOT, "base_url": None},
}
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
PORTAL_GITHUB_ADAPTER = "registry_bridge.fake_github.FakeGitHubClient"
GITHUB_REPO_OWNER = "synthetic-owner"
GITHUB_REPO_NAME = "synthetic-staging-repo"
GITHUB_WEBHOOK_SECRET = "test-webhook-secret"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ACCOUNT_RATE_LIMITS = {}
PORTAL_DEVELOPMENT_EMAIL_CAPTURE = True
